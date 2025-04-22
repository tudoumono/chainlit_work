const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  returnToSettings: () => ipcRenderer.invoke('return-to-settings')
});