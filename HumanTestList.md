# HumanTestList

人要親手做的檢查（真的 CLI、真的登入）。自動測試只用假的子程序，碰不到這些。

## 待測

- [ ] 2026-11-23 · 真的 codex 第一次呼叫 · `codex login`（Sign in with ChatGPT）後跑 `python -c "from chatgpt_login import ask; print(ask('請只回一個字：好'))"` · 印出 `Reply(text='好', usage={…}, …)`，usage 有數字
- [ ] 2026-11-23 · 沒登入時的錯誤字串 · `codex logout` 後跑同一行 · 丟 `AuthError`；若是一般 `LoginError`，把原文記下來補進 `_AUTH_RE`
- [ ] 2026-11-23 · 額度用完時的錯誤字串 · 下次真的遇到時記下錯誤原文 · 丟 `UsageLimitError`，`retry_after` 有秒數或 `resets` 有時間
- [ ] 2026-11-23 · 逾時會不會留下 node 程序（Windows，npm 的 codex.cmd）· `ask('寫一篇很長的文章', timeout=5)` 後看工作管理員 · 沒有殘留的 node／codex（有的話記下來，要改成殺整棵程序樹）

## 測過了

（還沒有）
