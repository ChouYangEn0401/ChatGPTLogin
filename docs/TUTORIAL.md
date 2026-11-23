# 新手教學：用自己的 ChatGPT 訂閱，在 Python 裡問一句話

這份教學寫給**沒什麼電腦概念的人**。照著一步一步做，每一步都寫了「要打什麼」「會看到什麼」「不是這樣怎麼辦」。
完整的說明在 [README](../README.md)。

---

## 這是什麼

- 這個套件（名字叫 `chatgpt_login`）讓你的 Python 程式可以問 OpenAI 的模型一句話、拿回一段文字。
- 它不是自己去連 OpenAI，而是**請你電腦上的官方 Codex 命令列工具（`codex`）去問**，用的是你自己的 ChatGPT 訂閱。
- 它不會讀、也不會存任何密碼或登入憑證。
- 它把 `codex` 關在「唯讀＋空資料夾」裡，只拿回文字；但 `codex` 本身沒辦法完全關掉工具，所以這是降低風險，不是保證（README 有寫）。
- 注意：這個套件還**沒有在真的 `codex` 上測過**。第一次用請照這份教學實際跑一次。

## 你需要準備什麼

| 要準備的 | 說明 |
|---|---|
| 一台 Windows 電腦 | 這份教學以 Windows 10／11 為例 |
| ChatGPT 帳號＋付費方案 | 例如 Plus、Pro、Business、Edu、Enterprise |
| 網路 | 安裝與登入都要連網 |
| 大約 20 分鐘 | |

先認識三個詞：

- **終端機**＝打指令的視窗（黑色或藍色底）。Windows 內建的叫 **PowerShell**。
- **指令**＝在終端機裡打的一行字，打完按 Enter 執行。
- **套件**＝別人寫好、可以裝進 Python 的程式。

---

## 步驟

### 步驟 1：打開 PowerShell

1. **做什麼**：開一個終端機視窗。
2. **打什麼**：按鍵盤左下角的 Windows 鍵，打 `PowerShell`，按 Enter。
3. **會看到什麼**：一個視窗，最後一行是 `PS` 開頭、`>` 結尾，中間是你目前所在的資料夾（每台電腦不同）：

   ```
   PS ...>
   ```

4. **不是這樣怎麼辦**：在「開始」按右鍵，選「Windows PowerShell」或「終端機」。

之後每一步的指令都在這個視窗裡打。**一次複製一行**，在視窗裡按右鍵貼上，按 Enter。

### 步驟 2：確認有沒有 Python

1. **做什麼**：看看電腦有沒有裝 Python（這個套件要靠它跑）。
2. **打什麼**：

   ```powershell
   python --version
   ```

3. **會看到什麼**：`Python 3.` 開頭的一行，例如：

   ```
   Python 3.12.8
   ```

   數字要是 **3.9 或更新**。

4. **不是這樣怎麼辦**：看到 `Python was not found` 或「無法辨識 'python' 詞彙」：到 <https://www.python.org/downloads/> 下載 Windows 安裝檔，
   安裝畫面第一頁**一定要勾「Add python.exe to PATH」**再按 Install。裝好後**關掉 PowerShell 再開一個新的**，重打一次。

### 步驟 3：安裝官方 Codex CLI

1. **做什麼**：裝 OpenAI 官方的 Codex 命令列工具（指令叫 `codex`）。
2. **打什麼**：

   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"
   ```

3. **會看到什麼**：一段安裝訊息，跑完回到 `PS ...>`。**關掉 PowerShell、重開一個**，再打：

   ```powershell
   codex --version
   ```

   會印出一行版本號。

4. **不是這樣怎麼辦**：
   - 重開後 `codex` 還是「無法辨識」：重新開機再試一次。
   - 也可以改用 npm 安裝（要先到 <https://nodejs.org/> 裝 Node.js）：`npm install -g @openai/codex`。
   - OpenAI 官方說明：<https://developers.openai.com/codex/cli>。

### 步驟 4：在終端機登入 ChatGPT

1. **做什麼**：用你自己的 ChatGPT 帳號登入。登入一次就好，之後這台電腦會記住。
2. **打什麼**：

   ```powershell
   codex login
   ```

3. **會看到什麼**：選 **Sign in with ChatGPT**，照指示在瀏覽器登入你的 ChatGPT 帳號。完成後回到 `PS ...>`。
   想確認有沒有登入，可以打：

   ```powershell
   codex login status
   ```

   它會告訴你目前用哪一種方式登入。
4. **不是這樣怎麼辦**：
   - 瀏覽器沒有自己打開：終端機上會有網址或代碼，照畫面指示做。
   - 選到 API key 登入也能用，但那是按量計費，不是訂閱。

### 步驟 5：開一個練習用的資料夾

1. **做什麼**：開一個新資料夾，等一下把套件裝在這裡。
2. **打什麼**（一次一行）：

   ```powershell
   mkdir $HOME\chatgpt-demo
   ```

   ```powershell
   cd $HOME\chatgpt-demo
   ```

3. **會看到什麼**：第一行列出新資料夾的資訊（最後一欄是 `chatgpt-demo`）；第二行之後，提示字變成 `...\chatgpt-demo>` 結尾。
4. **不是這樣怎麼辦**：看到「已經存在」，直接打第二行 `cd` 那行就好。

### 步驟 6：建一個「虛擬環境」並啟用

**虛擬環境**＝一個獨立的 Python 小房間，裝在裡面的套件不會影響電腦其他程式。

1. **做什麼**：建立並進入虛擬環境。
2. **打什麼**（一次一行）：

   ```powershell
   python -m venv .venv
   ```

   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```

3. **會看到什麼**：提示字最前面多了 `(.venv)`：

   ```
   (.venv) PS ...\chatgpt-demo>
   ```

4. **不是這樣怎麼辦**：
   - 出現紅字，裡面有「**因為這個系統上已停用指令碼執行**」：先打下面這行（只對這個視窗有效），再打一次 `.\.venv\Scripts\Activate.ps1`：

     ```powershell
     Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
     ```

   - **以後每次重開 PowerShell**，都要先 `cd $HOME\chatgpt-demo`，再打 `.\.venv\Scripts\Activate.ps1`。

### 步驟 7：安裝這個套件

1. **做什麼**：從這個專案的 GitHub Release 安裝套件。
2. **打什麼**：

   ```powershell
   python -m pip install https://github.com/ChouYangEn0401/ChatGPTLogin/releases/download/v0.2.0/chatgpt_login-0.2.0-py3-none-any.whl
   ```

3. **會看到什麼**：一些下載訊息，最後一行是 `Successfully installed` 開頭，裡面有 `0.2.0`。
4. **不是這樣怎麼辦**：連線錯誤就檢查網路，並確認整行（很長的網址）有完整複製。

### 步驟 8：問 ChatGPT 一句話

1. **做什麼**：用一行 Python 問一句話。這一步會用掉一點 ChatGPT 方案的額度。
2. **打什麼**：

   ```powershell
   python -c "from chatgpt_login import ask; print(ask('用一句話介紹台北').text)"
   ```

3. **會看到什麼**：等幾秒到幾十秒，印出一句回答，然後回到 `(.venv) PS ...>`。
4. **不是這樣怎麼辦**：出現一大段紅字時，**看最後一行**，對照下面的「常見問題」。

### 步驟 9：寫成一個小程式（可選）

1. **做什麼**：把問問題寫成一個檔案，還可以看到這次用了多少 token（文字量的單位）。
2. **打什麼**：

   ```powershell
   notepad ask.py
   ```

   記事本問「要建立新檔案嗎？」按「是」。貼上下面的內容，按 Ctrl+S 存檔，關掉記事本：

   ```python
   from chatgpt_login import ask, LoginError

   try:
       r = ask("用一句話介紹台北")
       print(r.text)
       print(r.usage)
   except LoginError as e:
       print("叫不動 Codex：", e)
   ```

   執行：

   ```powershell
   python ask.py
   ```

3. **會看到什麼**：第一行是回答；第二行是用量，例如 `{'input': …, 'cached_input': …, 'output': …, 'reasoning': …}`。
   失敗時印出 `叫不動 Codex：` 加上原因。
4. **不是這樣怎麼辦**：`ModuleNotFoundError: No module named 'chatgpt_login'`：提示字前面沒有 `(.venv)`，回到步驟 6。

---

## 常見問題

| 最後一行看到 | 意思 | 怎麼辦 |
|---|---|---|
| `` chatgpt_login.NotInstalledError: 這台電腦找不到 codex（OpenAI Codex CLI）。先安裝它並跑 `codex login`（選 Sign in with ChatGPT），再試一次。 `` | 沒裝 `codex`，或裝了但這個視窗還不知道 | 做步驟 3，然後重開 PowerShell（記得重新 `cd`、啟用虛擬環境） |
| `` chatgpt_login.AuthError: …是不是還沒 `codex login`… `` | 看起來是沒登入或登入過期 | 做步驟 4 重新登入 |
| `chatgpt_login.UsageLimitError: …` | 看起來是 ChatGPT 方案額度用完（有 5 小時的額度視窗） | 等一段時間再試 |
| `chatgpt_login.LoginError: Codex 沒有回任何文字（輸出裡沒有 agent_message）。` | `codex` 跑了但沒給答案 | 直接在終端機打 `codex` 看看能不能正常用；`codex` 更新一下再試 |
| `chatgpt_login.CallTimeoutError: Codex 超過 180 秒沒回。` | 等太久 | 再試一次；程式裡可以 `ask(..., timeout=300)` |

「沒登入」「額度用完」是看 `codex` 的錯誤訊息猜的，猜不到就是一般的 `LoginError`（README 有寫）。

---

## 使用聲明（一定要看）

- 這個套件用的是**你自己在這台電腦上登入的個人 ChatGPT 訂閱**。
- **不推薦拿個人訂閱服務別人**：不要轉售、共用，或做成給別人用的服務。官方文件也建議自動化改用 API 金鑰。
- **條款你自己看**：ChatGPT 有自己的使用條款，某種用法可不可以，請自己讀過、自己負責。
- 本專案只提供技術介面，與 OpenAI 無關。完整的聲明在 README 的〈訂閱登入的使用聲明〉。

---

## 全部做完了，接下來可以…

- 讀 README 的「給程式呼叫（統一介面）」：可以傳一整串對話訊息、指定模型（`model=`）、分辨每一種錯誤。
- 同一套寫法也能接 Claude（ClaudeLogin）與 GitHub Copilot（GithubCopilotLogin），三個套件名字都一樣。
- 想用一份設定檔切換本地模型、API 金鑰、訂閱：看 ntu_easy_llm 的 `remote/subscription/chatgpt` 來源。
