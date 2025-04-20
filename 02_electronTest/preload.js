// -------------------------------------------------
// Preload: Main ↔ Renderer の橋
// 公式: https://www.electronjs.org/docs/latest/tutorial/context-isolation
// -------------------------------------------------
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  /** JSON ファイルを選んで内容(文字列)を返す */
  openFile: () => ipcRenderer.invoke('dialog:openFile'),

  /** ウィンドウ制御のAPI（Mainに送信） */
  minimize: () => ipcRenderer.send('window-control', 'minimize'),
  maximize: () => ipcRenderer.send('window-control', 'maximize'),
  close: () => ipcRenderer.send('window-control', 'close'),

  sendOn: () => ipcRenderer.send('log:on', 'onイベント'),
  sendOnce: () => ipcRenderer.send('log:once', 'onceイベント'),
  sendInvoke: () => ipcRenderer.invoke('log:invoke', '戻り値ほしい'),

  // Mainからの返信を受けてRendererに渡す
  onLogReply: (callback) => ipcRenderer.on('log:reply', (_, msg) => callback(msg)),

  loadURL: (url) => ipcRenderer.send('url:load', url),

});