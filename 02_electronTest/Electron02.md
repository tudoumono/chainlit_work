以下では **「起動 → ウィンドウ生成 → UI 操作 → IPC → OS／ファイルアクセス → UI 反映」** という **1 本の“データ‑トランザクションの流れ”** を、実動する最小コードとともに段階的に追跡します。  
> #### ゴール  
> ユーザーが **“ファイルを開く” ボタン**を押すと、  
> 1. ファイル選択ダイアログが開く →  
> 2. JSON ファイルを選ぶ →  
> 3. その内容がパースされ、キー数が画面に表示される。  

---

## 0️⃣ 事前準備 & ファイル構成

```text
electron-learn-app/
├─ main.js        # Main Process（OS と通信）
├─ preload.js     # 安全な橋渡し
├─ index.html     # UI（Renderer）
├─ renderer.js    # UI ロジック
└─ package.json   # 依存 & スクリプト
```

---

## 1️⃣ アプリ起動シーケンス（ざっくり図解）

```text
npm start
  │
  └─▶ Electron CLI が main.js を実行
          │
          ├─ app.whenReady()
          │       │
          │       └─▶ BrowserWindow 作成
          │                 │
          │                 ├─ preload.js 先読み
          │                 │       │
          │                 │       └─▶ contextBridge で API 公開
          │                 │
          │                 └─ index.html 読込 → Renderer 起動
          │
          └─ ipcMain.handle() で OS/I/O ロジック待機
```

---

## 2️⃣ ソースコードと“なぜそう書くか”

### 2‑1. **main.js** – OS と IPC のハブ  
```js
// -------------------------------------------------
// Electron Main Process
// 公式: https://www.electronjs.org/docs/latest/api/app
// -------------------------------------------------
const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const fs = require('fs/promises'); // 非同期ファイル I/O
const path = require('path');

async function createWindow () {
  const win = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      // Preload で安全に API を渡す
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true, // ★ セキュリティ必須
      nodeIntegration: false  // ★ Renderer で Node を使わせない
    }
  });
  win.loadFile('index.html');
}

app.whenReady().then(createWindow);

// ========== ★ データフローの核心：Renderer からの要求を受け取る ==========
/**
 * Renderer から 'dialog:openFile' が invoke されたら
 * 1) ファイル選択ダイアログを表示
 * 2) 選択された JSON を読み取り文字列で返す
 */
ipcMain.handle('dialog:openFile', async () => {
  const { canceled, filePaths } = await dialog.showOpenDialog({
    properties: ['openFile'],
    filters: [{ name: 'JSON', extensions: ['json'] }]
  });
  if (canceled || filePaths.length === 0) return null;
  return fs.readFile(filePaths[0], 'utf-8');
});
// 公式: https://www.electronjs.org/docs/latest/api/ipc-main#ipcmainhandlechannel-listener
```

> **ポイント**  
> - `ipcMain.handle()` + `ipcRenderer.invoke()` パターンで **Promise 戻り**にすると、  
>   `async/await` でキレイに双方向通信。  
> - ファイル読みは OS 権限がある **Main** で実施 → Renderer に結果だけ返す。

---

### 2‑2. **preload.js** – 安全な公開 API  
```js
// -------------------------------------------------
// Preload: Main ↔ Renderer の橋
// 公式: https://www.electronjs.org/docs/latest/tutorial/context-isolation
// -------------------------------------------------
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  /** JSON ファイルを選んで内容(文字列)を返す */
  openFile: () => ipcRenderer.invoke('dialog:openFile')
});
```
> Renderer には **`electronAPI.openFile()`** しか見えない＝  
> Node.js や OS へのアクセス面を “最小限” に閉じ込め、XSS 防止。

---

### 2‑3. **index.html** – UI とイベントの入口  

```html
<!DOCTYPE html><html lang="ja"><head>
  <meta charset="UTF-8">
  <title>ファイル読込みデモ</title>
</head><body>
  <h1>JSON 読込みサンプル</h1>
  <button id="open">ファイルを開く</button>
  <div id="result"></div>

  <!-- Renderer ロジック -->
  <script src="renderer.js"></script>
</body></html>
```

---

### 2‑4. **renderer.js** – UI ↔ Preload API  

```js
// -------------------------------------------------
// Renderer Process: DOM 操作担当
// -------------------------------------------------
document.getElementById('open').addEventListener('click', async () => {
  const content = await window.electronAPI.openFile(); // Preload 経由で Main へ
  if (!content) return;

  const obj = JSON.parse(content);        // ここはブラウザ側だけで完結
  const count = Object.keys(obj).length;
  document.getElementById('result').textContent =
    `キー数は ${count} 件です`;
});
```
> Renderer には **ファイルパスどころか OS 権限も一切渡さない**。  
> 返ってくるのは「純粋な文字列のみ」。これが “安全設計” のキモ。

---

## 3️⃣ 実行時のトランザクション・タイムライン

| # | プロセス | イベント / 関数 | データがどう動くか |
|----|-----------|----------------|-------------------|
| ① | **Main** | `npm start` → `app.whenReady()` | Electron 起動 & BrowserWindow 作成 |
| ② | **Preload** | `contextBridge.exposeInMainWorld()` | `electronAPI.openFile` を Renderer に注入 |
| ③ | **Renderer** | ボタンクリック → `openFile()` | `ipcRenderer.invoke('dialog:openFile')` を送信 |
| ④ | **Main** | `ipcMain.handle('dialog:openFile')` | OS ダイアログ → `fs.readFile()` → JSON 文字列取得 |
| ⑤ | **Main → Renderer** | Promise 解決値として JSON 文字列を返す | 透過的にデータ移動（シリアライズ済み） |
| ⑥ | **Renderer** | `JSON.parse()` → DOM 更新 | UI に結果を描画 |

---

## 4️⃣ なぜこの流れを推奨するのか？

| 目的 | 採用 API / 機構 | 効果 |
|------|-----------------|-------|
| **① セキュリティ** | `contextIsolation`, Preload | XSS で Node.js が乗っ取られるリスクを遮断 |
| **② 可読性** | `ipcMain.handle` + `invoke` | `async/await` 1 行で Main ↔ Renderer 双方向通信 |
| **③ テスト & 再現性** | OS 依存 I/O を Main に集約 | Renderer は純粋 JS → ユニットテスト容易 |
| **④ パフォーマンス** | ファイル読みを Main 側で実施 | UI スレッドをブロックせず UX 滑らか |

---

## 5️⃣ 参考ドキュメント（公式）

- **IPC**: <https://www.electronjs.org/docs/latest/tutorial/ipc>  
- **Security Checklist**: <https://www.electronjs.org/docs/latest/tutorial/security>  
- **Dialog API**: <https://www.electronjs.org/docs/latest/api/dialog>  
- **BrowserWindow**: <https://www.electronjs.org/docs/latest/api/browser-window>  

---

### ✨ ここからの学習アイデア

1. **書き込みトランザクション**：`ipcMain.handle('saveFile', ...)` で JSON を保存し、Renderer から `invoke`。  
2. **SQL DB 連携**：Main で `better-sqlite3` を使い CRUD を実装。  
3. **リアルタイム通知**：Main で `new Notification()` 後、Renderer に状態を送って UI バッジ更新。  

> 「DB を絡めた完全な CRUD の流れも見たい」「TypeScript 化したコードを」など、次のステップがあれば遠慮なくご相談ください！