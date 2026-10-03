// Desktop shell of the page (version A): the same web/ files in an Electron window.
//
// CALIB3D_TEST=1 - test mode: the window is never shown, cannot take focus and sits off
// screen; pointer lock is refused. Tests drive it through Playwright without a single
// visible window on the user's screen.
'use strict';
const { app, BrowserWindow, Menu, dialog, ipcMain, screen, session } = require('electron');
const fs = require('fs');
const path = require('path');
const WindowState = require('./window-state');

const TEST = process.env.CALIB3D_TEST === '1';
const SIZE = { width: 1180, height: 820, minWidth: 900, minHeight: 620 };
const stateFile = () => path.join(app.getPath('userData'), 'window-state.json');
let win = null;

function createWindow() {
  const primary = screen.getPrimaryDisplay();
  const areas = [primary, ...screen.getAllDisplays().filter((d) => d.id !== primary.id)].map((d) => d.workArea);
  const placed = WindowState.restore(WindowState.load(stateFile()), areas, SIZE);
  win = new BrowserWindow({
    ...(TEST ? { x: -20000, y: -20000 } : placed.x !== undefined ? { x: placed.x, y: placed.y } : {}),
    width: placed.width,
    height: placed.height,
    minWidth: SIZE.minWidth,
    minHeight: SIZE.minHeight,
    title: 'Calibrate 3D Printer',
    icon: path.join(__dirname, '..', 'assets', 'icon.ico'),
    backgroundColor: '#12101f',
    show: false,
    focusable: !TEST,
    skipTaskbar: TEST,
    paintWhenInitiallyHidden: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      backgroundThrottling: false,
    },
  });
  win.setMenuBarVisibility(false);
  win.loadFile(path.join(__dirname, '..', 'web', 'index.html'));
  if (!TEST) {
    if (placed.maximized) win.maximize();
    win.once('ready-to-show', () => win.show());
  }
  const remember = () => { if (win && !win.isDestroyed() && !win.isMinimized() && !TEST) WindowState.save(stateFile(), WindowState.capture(win)); };
  for (const event of ['resized', 'moved', 'maximize', 'unmaximize']) win.on(event, remember);
  win.on('close', () => { if (win && !TEST) WindowState.save(stateFile(), WindowState.capture(win)); });
  win.on('closed', () => { win = null; });
  // links open nowhere inside the app
  win.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
}

function writeFiles(dir, files) {
  let count = 0;
  for (const f of files) {
    const name = path.basename(String(f.name));         // never a path from the page
    if (!name.toLowerCase().endsWith('.gcode')) continue;
    fs.writeFileSync(path.join(dir, name), String(f.text), 'utf8');
    count += 1;
  }
  return count;
}

ipcMain.handle('save-folder', async (_e, files) => {
  const r = await dialog.showOpenDialog(win, { properties: ['openDirectory', 'createDirectory'] });
  if (r.canceled || !r.filePaths.length) return null;
  return { path: r.filePaths[0], count: writeFiles(r.filePaths[0], files || []) };
});

ipcMain.handle('save-zip', async (_e, name, bytes) => {
  const r = await dialog.showSaveDialog(win, { defaultPath: path.basename(String(name || 'calibration.zip')),
    filters: [{ name: 'ZIP', extensions: ['zip'] }] });
  if (r.canceled || !r.filePath) return null;
  fs.writeFileSync(r.filePath, Buffer.from(bytes));
  return { path: r.filePath };
});

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  Menu.setApplicationMenu(null);
  app.on('second-instance', () => {
    if (!win || TEST) return;
    if (win.isMinimized()) win.restore();
    win.focus();
  });
  app.whenReady().then(() => {
    // The app needs no permissions at all: pointer lock, camera, notifications - all refused.
    session.defaultSession.setPermissionRequestHandler((_wc, _permission, cb) => cb(false));
    createWindow();
  });
  app.on('window-all-closed', () => app.quit());
}

module.exports = { writeFiles };
