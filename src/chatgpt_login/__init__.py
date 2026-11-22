"""
chatgpt_login: 用「使用者自己的 ChatGPT 訂閱」叫 OpenAI，做法是驅動官方的 `codex` 命令列（`codex exec --json`）。

    from chatgpt_login import ask
    reply = ask("請只回一個字：好")          # Reply(text=..., usage={...}, thread_id=...)

為什麼這樣做（調查 2026-11-13，官方文件 learn.chatgpt.com/docs：auth、non-interactive-mode、pricing）：
- OpenAI 文件明講 `codex exec`、Codex SDK、可腳本化的流程可以用 ChatGPT 方案的額度，使用者先自己 `codex login`。
- **這個套件從頭到尾不讀、不碰 `~/.codex/auth.json`**（文件說它跟密碼一樣）。登入狀態由官方 binary 自己管。
  從 auth.json 抽 token 再自己打 ChatGPT 後端：文件沒有允許，也沒有明文禁止，風險高，所以不做。
- 文件建議自動化用 API 金鑰；用訂閱跑 24/7 的機器人是灰色地帶，用量算在 ChatGPT 方案的額度裡（有 5 小時視窗上限）。

跟 `claude -p --tools ""` 的差別（照實說）：codex 是 agent，沒有「一個工具都不給」的旗標。這裡的防護是
唯讀沙盒（預設）＋空的工作資料夾＋--ephemeral（不留 session 檔）＋--ignore-rules。它仍可能試著跑唯讀的 shell 指令；
呼叫端（SYNOX）不要把這個當成「保證只回文字」。

沒在真的 codex 上驗證過：寫這個時這台沒裝 codex，旗標與事件格式照官方文件寫、用假的 runner 測。
`-m`（選模型）文件那頁沒寫，是照 codex 一貫的旗標加的；不指定模型就不會帶。

統一呼叫介面（0.2.0，`INTERFACE_VERSION = "1"`；`claude_subscription`、`github_copilot_login` 用同一組名字）：
`ask()` 的第一個參數可以是訊息清單、`Result`（＝`Reply`）有 `text`／`usage`／`model`／`raw`，
錯誤分成 `UsageLimitError`／`AuthError`／`NotInstalledError`／`CallTimeoutError`，全都是 `LoginError`。
額度用完、沒登入是**看錯誤訊息的字猜的**（沒有實測），猜不到就是一般的 `LoginError`。
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

__version__ = "0.2.0"

__all__ = [
    "ask", "find_codex", "Reply", "LoginError", "NOT_FOUND", "argv", "parse_events",
    # 統一呼叫介面
    "INTERFACE_VERSION", "CAPABILITIES", "Result", "UsageLimitError", "AuthError", "NotInstalledError",
    "CallTimeoutError", "flatten_messages", "__version__",
]

NOT_FOUND = "這台電腦找不到 codex（OpenAI Codex CLI）。先安裝它並跑 `codex login`（選 Sign in with ChatGPT），再試一次。"
INTERFACE_VERSION = "1"

# 能力照實標（給包裝的程式決定能不能用這個來源）。
CAPABILITIES = {
    "interface": INTERFACE_VERSION,
    "backend": "codex exec --json",
    "text": True,
    "tools": False,               # 沒有 function calling（codex 自己可能跑唯讀指令，見 agent_sandbox）
    "agent_sandbox": "read-only", # codex 是 agent，關不掉它自己的工具；只能限制在唯讀沙盒＋空資料夾
    "stream": False,
    "usage": True,                # turn.completed 帶 token 用量
    "cost": False,
    "system": "prepended",        # 沒用系統提示旗標：接在提示最前面
    "messages": "flattened",      # 多輪訊息攤成一段文字
    "images": False,
    "json_schema": False,
    "default_model": "",          # 空＝codex 自己的預設
    "verified_with_real_cli": False,
}


# --------------------------------------------------------------------------- #
# 錯誤（統一介面：每一種都是 LoginError，.kind 是分類字串）
# --------------------------------------------------------------------------- #
class LoginError(Exception):
    """叫不動；訊息是一句給人看的話。統一介面的共同基底，``kind`` 是分類字串。"""

    kind = "unknown"


class UsageLimitError(LoginError):
    """ChatGPT 方案額度用完／被限流（看錯誤訊息的字猜的）。``resets``：重置時間原文；``retry_after``：秒數，猜不到是 None。"""

    kind = "quota_exhausted"

    def __init__(self, message: str, resets: str = "", retry_after: Optional[float] = None):
        super().__init__(message)
        self.resets = resets
        self.retry_after = retry_after


class AuthError(LoginError):
    """沒登入、登入過期（看錯誤訊息的字猜的）。"""

    kind = "auth_invalid"


class NotInstalledError(LoginError):
    """找不到 codex，或叫不起來。"""

    kind = "not_installed"


class CallTimeoutError(LoginError):
    """超過 timeout 秒沒回。"""

    kind = "timeout"


# 錯誤訊息的猜法【推測：沒有實測】。只看 codex 自己的輸出，不看這個套件加的提示句。
_AUTH_RE = re.compile(
    r"(?i)(not (?:logged|signed) in|no authentication|not authenticated|authentication (?:failed|required)|"
    r"please (?:log|sign) ?in|(?:log|sign) ?in again|unauthori[sz]ed|codex login|refresh(?:_| )token|"
    r"(?:token|credentials?) (?:has |have )?expired|expired (?:token|credentials?)|could not be refreshed|"
    r"re-?authenticate|(?:status|http|code|error)\W{0,3}401\b)")
_LIMIT_RE = re.compile(
    r"(?i)(quota|usage.limit|limit (?:reached|exceeded)|exceeded .{0,40}?(?:limit|requests|allowance)|"
    r"rate.?limit|too many requests|(?:status|http|code|error)\W{0,3}429\b)")
_RESET_RE = re.compile(r"(?i)(?:try again|retry|resets?)\s+(in|at|after|on)\s+([^.\n]{1,60})")
_DURATION_RE = re.compile(r"(?i)(\d+(?:\.\d+)?)\s*(d(?:ays?)?|h(?:ours?|rs?)?|m(?:in(?:ute)?s?)?|s(?:ec(?:ond)?s?)?)\b")
_UNIT_SECONDS = {"d": 86400, "h": 3600, "m": 60, "s": 1}


def _reset_hint(raw: str) -> Tuple[str, Optional[float]]:
    """「try again in 2 hours 5 minutes」→ ("2 hours 5 minutes", 7500.0)；「at 5pm」只給原文、秒數 None。"""
    match = _RESET_RE.search(raw or "")
    if not match:
        return "", None
    text = match.group(2).strip()
    if match.group(1).lower() not in ("in", "after"):
        return text, None
    seconds = sum(float(n) * _UNIT_SECONDS[u[0].lower()] for n, u in _DURATION_RE.findall(text))
    return text, (seconds or None)


def _failure(message: str, raw: str) -> LoginError:
    """依 codex 的原始輸出 raw 決定錯誤種類；猜不到就是一般的 LoginError。"""
    raw = " ".join(str(raw or "").split())
    if _AUTH_RE.search(raw):
        return AuthError(message)
    if _LIMIT_RE.search(raw):
        resets, retry_after = _reset_hint(raw)
        return UsageLimitError(message, resets=resets, retry_after=retry_after)
    return LoginError(message)


# --------------------------------------------------------------------------- #
# 訊息清單 → 一段提示（三個訂閱登入套件的寫法一模一樣）
# --------------------------------------------------------------------------- #
_MULTI_TURN_HEAD = ("Below is a conversation between a user and an assistant. "
                    "Reply as the assistant to the last user message, with the assistant's reply only.")
_ROLE_HEAD = {"user": "### User", "assistant": "### Assistant"}


def _content_text(content: Any) -> str:
    """訊息內容 → 文字。字串原樣；OpenAI 式 parts 清單只收 type=text，其他（圖片…）丟 ValueError。"""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (list, tuple)):
        parts = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and part.get("type", "text") == "text":
                parts.append(str(part.get("text") or ""))
            else:
                kind = part.get("type") if isinstance(part, dict) else type(part).__name__
                raise ValueError(f"這個來源只收文字，不支援 {kind!r} 內容（例如圖片）。")
        return "".join(parts)
    raise ValueError(f"訊息內容要是字串或文字 parts 清單，收到 {type(content).__name__}。")


def flatten_messages(messages_or_prompt: Any, system: Optional[str] = None) -> tuple:
    """字串或訊息清單 → ``(system, prompt)``（三個訂閱登入套件的寫法一模一樣）。

    * 字串：原樣當 prompt，system 照給的。
    * 清單：每則是 dict（``role``、``content``）或有 ``.role``／``.content`` 的物件。
      ``system`` 的內容收進 system（跟參數給的用空行接在後面）；``user``／``assistant`` 是對話；
      其他角色（``tool``…）丟 ValueError——這個來源沒有工具呼叫。內容可以是字串或 OpenAI 式 parts（只收文字）。
    * 只有一則 user（可以加 system）：prompt 就是那則原文。多輪：攤成一段逐字稿，最後一則必須是 user。"""
    if isinstance(messages_or_prompt, str):
        return system, messages_or_prompt
    if messages_or_prompt is None or isinstance(messages_or_prompt, (bytes, dict)):
        raise ValueError("要給字串，或訊息清單（每則有 role、content）。")
    systems, turns = [], []
    for msg in messages_or_prompt:
        if isinstance(msg, dict):
            role, content = msg.get("role"), msg.get("content")
        else:
            role, content = getattr(msg, "role", None), getattr(msg, "content", None)
        role = str(role or "").lower()
        text = _content_text(content)
        if role == "system":
            if text.strip():
                systems.append(text)
        elif role in _ROLE_HEAD:
            turns.append((role, text))
        else:
            raise ValueError(f"不支援的訊息角色 {role!r}：這個來源只有 system／user／assistant，沒有工具呼叫。")
    if not turns or turns[-1][0] != "user":
        raise ValueError("訊息清單裡最後一則（system 以外）必須是 user。")
    merged = "\n\n".join(s for s in ([system] if system else []) + systems) or system
    if len(turns) == 1:
        return merged, turns[0][1]
    body = "\n\n".join(f"{_ROLE_HEAD[role]}\n{text}" for role, text in turns)
    return merged, f"{_MULTI_TURN_HEAD}\n\n{body}"


def _with_system(system: Optional[str], prompt: str) -> str:
    """沒用系統提示旗標：把 system 接在提示最前面。"""
    if not system:
        return prompt
    return f"[Instructions]\n{system}\n\n[Request]\n{prompt}"


# --------------------------------------------------------------------------- #
# 呼叫
# --------------------------------------------------------------------------- #
@dataclass
class Reply:
    text: str
    usage: Dict[str, int] = field(default_factory=dict)    # input / cached_input / output / reasoning
    thread_id: str = ""
    model: str = ""                                         # 呼叫時指定的模型；沒指定（codex 自己的預設）是空字串
    raw: Any = None                                         # 除錯用：解析到的事件清單；內容不保證


Result = Reply


def find_codex() -> Optional[str]:
    """PATH 上的 codex；沒有就看 npm 全域安裝的固定位置（Windows 的 %APPDATA%\\npm）。"""
    found = shutil.which("codex")
    if found:
        return found
    appdata = os.environ.get("APPDATA")
    if appdata:
        for name in ("codex.cmd", "codex.exe", "codex"):
            path = os.path.join(appdata, "npm", name)
            if os.path.isfile(path):
                return path
    return None


def argv(exe: str, *, model: str = "", ignore_user_config: bool = False) -> List[str]:
    """prompt 一律從 stdin 給（`-`）：不放在命令列，避免長度限制與被別的行程看到。"""
    out = [exe, "exec", "--json", "--sandbox", "read-only", "--skip-git-repo-check", "--ephemeral", "--ignore-rules"]
    if ignore_user_config:
        out.append("--ignore-user-config")     # 不吃 config.toml 裡的 MCP／設定；登入存放方式若寫在那裡可能登不進去，所以預設不帶
    if model:
        out += ["-m", model]
    out.append("-")
    return out


def parse_events(stdout: str) -> Reply:
    """--json 的 JSONL → Reply。最後一個 agent_message 是答案；turn.completed 帶用量；
    turn.failed／error 丟 LoginError（認得出來的話是 UsageLimitError／AuthError）。"""
    text, usage, thread, failure, events = "", {}, "", "", []
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if not isinstance(ev, dict):
            continue
        events.append(ev)
        kind = ev.get("type")
        if kind == "thread.started":
            thread = str(ev.get("thread_id") or "")
        elif kind == "item.completed" and isinstance(ev.get("item"), dict) and ev["item"].get("type") == "agent_message":
            text = str(ev["item"].get("text") or "")
        elif kind == "turn.completed" and isinstance(ev.get("usage"), dict):
            u = ev["usage"]
            usage = {"input": int(u.get("input_tokens") or 0), "cached_input": int(u.get("cached_input_tokens") or 0),
                     "output": int(u.get("output_tokens") or 0), "reasoning": int(u.get("reasoning_output_tokens") or 0)}
        elif kind in ("turn.failed", "error"):
            err = ev.get("error") if isinstance(ev.get("error"), dict) else {}
            failure = str(err.get("message") or ev.get("message") or "（沒有訊息）")
    if failure:
        raise _failure(f"Codex 回了錯誤：{failure}。是不是還沒 `codex login`、或 ChatGPT 方案的額度用完了？", failure)
    if not text:
        raise LoginError("Codex 沒有回任何文字（輸出裡沒有 agent_message）。")
    return Reply(text=text, usage=usage, thread_id=thread, raw=events)


@contextlib.contextmanager
def _scratch_dir():
    """新的空暫存資料夾，用完刪掉（刪不掉就算了）。Python 3.9 沒有 TemporaryDirectory(ignore_cleanup_errors=…)。"""
    path = tempfile.mkdtemp(prefix="chatgpt_login-")
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def ask(prompt: Any, *, model: Optional[str] = None, system: Optional[str] = None, timeout: float = 180.0,
        workdir: str = "", ignore_user_config: bool = False, runner: Optional[Callable] = None,
        which: Optional[Callable[[], Optional[str]]] = None) -> Reply:
    """問一次。prompt 可以是字串或訊息清單（見 flatten_messages）；system 接在提示最前面。

    model=None／空字串＝codex 自己的預設。runner／which 給測試換假的。workdir 空＝每次用一個新的空暫存資料夾。
    錯誤：NotInstalledError、CallTimeoutError、AuthError、UsageLimitError、其他 LoginError；訊息清單格式不對丟 ValueError。"""
    system, text = flatten_messages(prompt, system)
    text = _with_system(system, text)
    model = model or ""
    exe = (which or find_codex)()
    if not exe:
        raise NotInstalledError(NOT_FOUND)
    run = runner or subprocess.run
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    def go(cwd: str):
        try:
            return run(argv(exe, model=model, ignore_user_config=ignore_user_config), input=text, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=timeout, cwd=cwd, creationflags=flags)
        except subprocess.TimeoutExpired:
            raise CallTimeoutError(f"Codex 超過 {int(timeout)} 秒沒回。")
        except OSError as e:
            raise NotInstalledError(f"叫不起 codex：{e}")

    if workdir:
        os.makedirs(workdir, exist_ok=True)
        done = go(workdir)
    else:
        with _scratch_dir() as tmp:
            done = go(tmp)
    try:
        reply = parse_events(done.stdout or "")
    except LoginError as err:
        if type(err) is not LoginError:      # 已經認出是額度或登入問題
            raise
        if done.returncode != 0:
            tail = (done.stderr or "").strip()[-200:]
            raise _failure(f"Codex 結束碼 {done.returncode}：{tail or '（沒有訊息）'}。是不是還沒 `codex login`？",
                           (done.stderr or "")[-2000:]) from None
        raise
    reply.model = model
    return reply
