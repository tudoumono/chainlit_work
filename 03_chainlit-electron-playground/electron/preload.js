const { contextBridge, ipcRenderer } = require('electron');

// レンダラープロセスで使用する安全なAPIを公開
contextBridge.exposeInMainWorld('electronAPI', {
  // .envファイル関連
  readEnv: () => ipcRenderer.invoke('read-env'),
  writeEnv: (content) => ipcRenderer.invoke('write-env', content),
  
  // Chainlit関連
  startChainlit: () => ipcRenderer.invoke('start-chainlit'),
  openChainlit: () => ipcRenderer.invoke('open-chainlit')
});