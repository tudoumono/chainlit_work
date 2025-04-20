// -------------------------------------------------
// Electron Main Process
// 公式: https://www.electronjs.org/docs/latest/api/app
// -------------------------------------------------
const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const fs = require('fs/promises'); // 非同期ファイル I/O
const path = require('path');

// winをグローバルに定義（他の関数でも見えるように）
let win;

async function createWindow () {
  win = new BrowserWindow({
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



// 🔽 追加：ウィンドウ操作の処理
ipcMain.on('window-control', (_, action) => {
    if (!win) return;
    switch (action) {
      case 'minimize':
        win.minimize();
        break;
      case 'maximize':
        win.isMaximized() ? win.unmaximize() : win.maximize();
        break;
      case 'close':
        win.close();
        break;
    }
  });

// on：何回でも反応する
ipcMain.on('log:on', (event, msg) => {
    event.sender.send('log:reply', `on: ${msg} を受け取りました`);
  });
  
  // once：最初の1回だけ反応する
  ipcMain.once('log:once', (event, msg) => {
    event.sender.send('log:reply', `once: ${msg} を受け取りました（1回きり）`);
  });
  
  // invoke/handle：応答も返す
  ipcMain.handle('log:invoke', async (_, msg) => {
    return `invoke: ${msg} に応答します（←これは戻り値）`;
  });



// URL受信 → そのURLを読み込む
  ipcMain.on('url:load', (_, url) => {
    if (!win) {
        event.sender.send('log:reply', 'ウィンドウがまだ存在していません。');
        return;
      }
      if (!/^https?:\/\//.test(url)) {
        event.sender.send('log:reply', 'URLの形式が正しくありません。http(s)://で始めてください。');
        return;
      }
    
      win.loadURL(url);
  });