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
  openChainlit: () => ipcRenderer.invoke('open-chainlit'),
  
  // 設定画面に戻る
  returnToSettings: () => ipcRenderer.invoke('return-to-settings'),
  
  // パス情報の取得
  getPaths: () => ipcRenderer.invoke('get-paths'),
  
  // 最新のチャットログ情報を取得
  getLatestChatLog: () => ipcRenderer.invoke('getLatestChatLog'),
  
  // 最新のチャットログを開く
  openLatestChatLog: () => ipcRenderer.invoke('openLatestChatLog'),
  
  // ログファイルを開く（従来の機能）
  openLogFile: () => ipcRenderer.invoke('open-log-file'),
  
  // 実行ディレクトリを表示
  showExeDir: () => ipcRenderer.invoke('show-exe-dir')
});