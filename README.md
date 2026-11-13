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

## 之後
- SYNOX 的 `ChatAdapter` 薄包一層（`kind: "chatgpt_login"`，`supports_tools=False` 走文字協定）。
- 官方更正式的路：Codex app-server（stdio JSON）、Sign in with ChatGPT 的 open-source client 登記（取得屬於 SYNOX 自己的 token）。
