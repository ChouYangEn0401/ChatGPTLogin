# chatgpt_login

> 非官方套件，與 OpenAI 無關。它只是驅動你自己電腦上、已登入的官方 `codex` 命令列，用你自己的 ChatGPT 訂閱；不讀、不存任何 token。姊妹套件：[GithubCopilotLogin](https://github.com/ChouYangEn0401/GithubCopilotLogin)。

用你自己的 ChatGPT 訂閱，從 Python 叫 OpenAI：驅動官方的 `codex exec --json`，**不讀 `~/.codex/auth.json`**。
跟 `claude -p` 那個套件同一個思路。沒有相依套件。

```python
from chatgpt_login import ask
print(ask("請只回一個字：好").text)   # 先在終端機跑過 `codex login`（Sign in with ChatGPT）
```

## 先看這幾件事
- **許可（2026-11-13 官方文件）**：`codex exec`／Codex SDK／可腳本化流程可以用 ChatGPT 方案額度，使用者自己 `codex login`。
  文件同時說「自動化建議用 API 金鑰」；用訂閱跑 24/7 是灰色地帶，額度有 5 小時視窗（429 時換成 API 金鑰）。
- **不做**：抽 auth.json 的 token 自己打後端、多人共用一個登入、把自己的訂閱開給別人。
- **不像 `claude --tools ""`**：codex 不能完全關工具。這裡用唯讀沙盒＋空資料夾＋`--ephemeral`＋`--ignore-rules` 降低風險，不是保證。
- **沒在真的 codex 上測過**（寫的時候那台沒裝）；測試用假的 runner。第一次用請先
  `python -c "from chatgpt_login import ask; print(ask('hi'))"` 確認。

## 給程式呼叫（統一介面，0.2.0）

`chatgpt_login`、`claude_subscription`（ClaudeLogin）、`github_copilot_login` 三個訂閱登入套件用**同一組名字**（`INTERFACE_VERSION = "1"`），
包裝它們的程式可以用同一段程式碼接三家：

```python
from chatgpt_login import ask, LoginError, UsageLimitError, AuthError, NotInstalledError, CallTimeoutError

r = ask([{"role": "system", "content": "回答要短"},
         {"role": "user", "content": "一句話介紹台北"}], model=None, timeout=120)
print(r.text, r.model, r.usage)          # usage: {"input", "cached_input", "output", "reasoning"}
```

| 名字 | 說明 |
|---|---|
| `ask(prompt, *, model=None, system=None, timeout=180.0, workdir="", ignore_user_config=False, runner=None, which=None) -> Result` | `prompt` 是字串或訊息清單（一律從 stdin 送）；`model=None`＝codex 自己的預設；`system` 接在提示最前面 |
| `Result`（＝`Reply`） | `.text`、`.usage`、`.model`（指定的模型，沒指定是 `""`）、`.raw`（解析到的事件清單，除錯用）；另有 `.thread_id` |
| `LoginError` | 共同基底；`.kind` 是分類字串 |
| `UsageLimitError` | `kind="quota_exhausted"`；`.resets`（重置時間原文）、`.retry_after`（「try again in 2 hours」這種才算得出秒數，否則 `None`） |
| `AuthError` | `kind="auth_invalid"`：沒登入、登入過期 |
| `NotInstalledError` | `kind="not_installed"`：找不到 codex、叫不起來 |
| `CallTimeoutError` | `kind="timeout"` |
| `CAPABILITIES` | 能力照實標：沒有工具呼叫（但 codex 可能自己跑唯讀指令，`agent_sandbox="read-only"`）、沒有串流、有用量、不收圖、多輪攤平、沒用真的 codex 驗證過 |
| `flatten_messages(messages, system=None)` | 訊息清單 → `(system, prompt)`；三個套件寫法一樣 |

- 訊息清單：每則 `role`＋`content`（字串或只含文字的 parts）；`tool` 角色、圖片、最後一則不是 `user` → `ValueError`。
  多輪會攤成一段逐字稿送出（每次都是 `--ephemeral` 的新對話）。
- **額度用完、沒登入是看錯誤訊息的字猜的**（沒有實測）；猜不到就是一般的 `LoginError`。
- 舊的用法不變：`ask("…")`、`Reply`、`parse_events`、`except LoginError` 照舊接得到所有錯誤。

## 之後
- SYNOX 的 `ChatAdapter` 薄包一層（`kind: "chatgpt_login"`，`supports_tools=False` 走文字協定）。
- 官方更正式的路：Codex app-server（stdio JSON）、Sign in with ChatGPT 的 open-source client 登記（取得屬於 SYNOX 自己的 token）。
