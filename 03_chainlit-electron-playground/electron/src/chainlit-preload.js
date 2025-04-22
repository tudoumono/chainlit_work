const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  returnToSettings: () => ipcRenderer.invoke('return-to-settings'),
  openLogFile: () => ipcRenderer.invoke('open-log-file'),
  showExeDir: () => ipcRenderer.invoke('show-exe-dir'),
  getPaths: () => ipcRenderer.invoke('get-paths')
});