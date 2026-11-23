# HumanTestList

人要親手做的檢查（真的 CLI、真的登入）。自動測試只用假的子程序，碰不到這些。

## 待測

- [ ] 2026-11-23 · 真的 codex 第一次呼叫 · `codex login`（Sign in with ChatGPT）後跑 `python -c "from chatgpt_login import ask; print(ask('請只回一個字：好'))"` · 印出 `Reply(text='好', usage={…}, …)`，usage 有數字
- [ ] 2026-11-23 · 沒登入時的錯誤字串 · `codex logout` 後跑同一行 · 丟 `AuthError`；若是一般 `LoginError`，把原文記下來補進 `_AUTH_RE`
- [ ] 2026-11-23 · 額度用完時的錯誤字串 · 下次真的遇到時記下錯誤原文 · 丟 `UsageLimitError`，`retry_after` 有秒數或 `resets` 有時間
- [ ] 2026-11-23 · 逾時會不會留下 node 程序（Windows，npm 的 codex.cmd）· `ask('寫一篇很長的文章', timeout=5)` 後看工作管理員 · 沒有殘留的 node／codex（有的話記下來，要改成殺整棵程序樹）
- [ ] 2026-11-23 · 新手教學能照著走完 · 找一台新電腦，照 docs/TUTORIAL.md 從頭走一遍 · 每一步「會看到什麼」都對得上；對不上的記下實際畫面交回改教學
- [ ] 2026-11-23 · 真的 codex CLI 能不能跑（Windows）· 新電腦上用官方安裝指令裝 codex → 重開 PowerShell 打 `codex --version` → `codex login` → 教學步驟 8 的 `python -c …` · 有回答；記下官方安裝程式有沒有把 `%LOCALAPPDATA%\Programs\OpenAI\Codex\bin` 加進 PATH（沒有的話套件找不到 codex）、`codex login` 是直接開瀏覽器還是先讓你選、唯讀沙盒或資料夾信任有沒有擋住呼叫（原文）

## 測過了

（還沒有）
