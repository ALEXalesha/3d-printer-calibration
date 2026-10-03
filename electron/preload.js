// The only bridge between the page and Node: saving files where the user chooses.
'use strict';
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('calib3dDesktop', {
  saveFolder: (files) => ipcRenderer.invoke('save-folder', files),
  saveZip: (name, bytes) => ipcRenderer.invoke('save-zip', name, bytes),
});
