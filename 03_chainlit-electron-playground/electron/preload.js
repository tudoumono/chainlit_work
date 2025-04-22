const { contextBridge, ipcRenderer } = require('electron');

// IPC通信のためのAPIをレンダラープロセスに公開
contextBridge.exposeInMainWorld('api', {
  // .envファイルの読み込み
  readEnv: () => ipcRenderer.invoke('read-env'),
  
  // .envファイルの書き込み
  writeEnv: (content) => ipcRenderer.invoke('write-env', content),
  
  // Chainlitサーバーの起動
  startChainlit: () => ipcRenderer.invoke('start-chainlit'),
  
  // Chainlitページを開く
  openChainlit: () => ipcRenderer.invoke('open-chainlit')
});