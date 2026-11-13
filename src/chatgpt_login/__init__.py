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
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

__all__ = ["ask", "find_codex", "Reply", "LoginError", "NOT_FOUND", "argv", "parse_events"]

NOT_FOUND = "這台電腦找不到 codex（OpenAI Codex CLI）。先安裝它並跑 `codex login`（選 Sign in with ChatGPT），再試一次。"


class LoginError(Exception):
    """叫不動；訊息是一句給人看的話。"""


@dataclass
class Reply:
    text: str
    usage: Dict[str, int] = field(default_factory=dict)    # input / cached_input / output / reasoning
    thread_id: str = ""


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
    """--json 的 JSONL → Reply。最後一個 agent_message 是答案；turn.completed 帶用量；turn.failed／error 丟 LoginError。"""
    text, usage, thread, failure = "", {}, "", ""
    for line in (stdout or "").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
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
        raise LoginError(f"Codex 回了錯誤：{failure}。是不是還沒 `codex login`、或 ChatGPT 方案的額度用完了？")
    if not text:
        raise LoginError("Codex 沒有回任何文字（輸出裡沒有 agent_message）。")
    return Reply(text=text, usage=usage, thread_id=thread)


def ask(prompt: str, *, model: str = "", timeout: float = 180.0, workdir: str = "", ignore_user_config: bool = False,
        runner: Optional[Callable] = None, which: Optional[Callable[[], Optional[str]]] = None) -> Reply:
    """問一次。runner／which 給測試換假的。workdir 空＝每次用一個新的空暫存資料夾。"""
    exe = (which or find_codex)()
    if not exe:
        raise LoginError(NOT_FOUND)
    run = runner or subprocess.run
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    def go(cwd: str):
        try:
            return run(argv(exe, model=model, ignore_user_config=ignore_user_config), input=prompt, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=timeout, cwd=cwd, creationflags=flags)
        except subprocess.TimeoutExpired:
            raise LoginError(f"Codex 超過 {int(timeout)} 秒沒回。")
        except OSError as e:
            raise LoginError(f"叫不起 codex：{e}")

    if workdir:
        os.makedirs(workdir, exist_ok=True)
        done = go(workdir)
    else:
        with tempfile.TemporaryDirectory(prefix="chatgpt_login-", ignore_cleanup_errors=True) as tmp:
            done = go(tmp)
    try:
        return parse_events(done.stdout or "")
    except LoginError:
        if done.returncode != 0:
            tail = (done.stderr or "").strip()[-200:]
            raise LoginError(f"Codex 結束碼 {done.returncode}：{tail or '（沒有訊息）'}。是不是還沒 `codex login`？")
        raise
