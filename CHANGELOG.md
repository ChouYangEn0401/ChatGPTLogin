# Changelog

格式參考 [Keep a Changelog 1.1.0](https://keepachangelog.com/zh-TW/1.1.0/)，版號遵循 [SemVer 2.0.0](https://semver.org/lang/zh-TW/)。

## [Unreleased]

## [0.2.0] - 2026-11-23

### Added
- 統一呼叫介面（`INTERFACE_VERSION = "1"`；`claude_subscription`、`github_copilot_login` 用同一組名字），給多來源的 LLM 函式庫包裝用：
  - `ask()` 的第一個參數可以是訊息清單；新參數 `system`（接在提示最前面）；`model` 預設改成 `None`（＝codex 自己的預設，跟以前的 `""` 一樣）。
  - `flatten_messages(messages, system=None) -> (system, prompt)`。
  - `Reply` 多了 `model`、`raw`（解析到的事件清單）；別名 `Result`。
  - 錯誤分類：`UsageLimitError`（`.resets`、`.retry_after`）、`AuthError`、`NotInstalledError`、`CallTimeoutError`，全都是 `LoginError` 的子類別，各有 `.kind`。額度與登入是看錯誤訊息的字猜的。
  - `CAPABILITIES`：能力照實標。
  - `__version__`。
  - `tests/test_interface.py`。
- 這份 CHANGELOG。

### Fixed
- 結束碼不是 0、但 `turn.failed` 已經認出是額度或登入問題時，不再被蓋成一般的「結束碼 N」錯誤。
- `--json` 輸出裡有不是物件的 JSON 行時不再丟 `AttributeError`。
- 暫存資料夾改用 `mkdtemp`＋`rmtree(ignore_errors=True)`：`TemporaryDirectory(ignore_cleanup_errors=…)` 要 Python 3.10，跟 `requires-python = ">=3.9"` 不合。

## [0.1.0] - 2026-11-13

### Added
- `ask()`：驅動官方 `codex exec --json`（唯讀沙盒、空資料夾、`--ephemeral`、`--ignore-rules`），prompt 走 stdin，不讀 `~/.codex/auth.json`。
