const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  onDownloadStatus: (callback) => {
    ipcRenderer.on('download-status', (event, status) => callback(status))
  }
})
