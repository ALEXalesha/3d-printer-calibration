// The Electron shell: invisible test window, saving to a folder and to a zip, window place.
const fs = require('fs');
const os = require('os');
const path = require('path');
const { test, expect, _electron: electron } = require('@playwright/test');

const ROOT = path.join(__dirname, '..', '..');

async function launch(dataDir, extraEnv) {
  const app = await electron.launch({
    executablePath: require('electron'),
    args: [ROOT, '--user-data-dir=' + dataDir],
    env: Object.assign({}, process.env, { CALIB3D_TEST: '1' }, extraEnv || {}),
    cwd: ROOT,
  });
  const win = await app.firstWindow();
  await win.addInitScript(() => {
    Element.prototype.requestPointerLock = function () { window.__pl = (window.__pl || 0) + 1; };
  });
  await win.waitForFunction(() => window.calib3dApp && window.calib3dApp.done(), null, { timeout: 60000 });
  return { app, win };
}

function tmp(prefix) { return fs.mkdtempSync(path.join(os.tmpdir(), prefix)); }

test('test window is invisible, unfocusable and off screen', async () => {
  const data = tmp('calib3d-app-');
  const { app, win } = await launch(data);
  try {
    const st = await app.evaluate(({ BrowserWindow }) => {
      const w = BrowserWindow.getAllWindows()[0];
      return { visible: w.isVisible(), focusable: w.isFocusable(), bounds: w.getBounds(), title: w.getTitle() };
    });
    expect(st.visible).toBe(false);
    expect(st.focusable).toBe(false);
    expect(st.bounds.x).toBeLessThan(-10000);
    expect(await win.evaluate(() => typeof window.calib3dDesktop.saveFolder)).toBe('function');
    expect(await win.evaluate(() => typeof require)).toBe('undefined');          // no Node in the page
  } finally {
    await app.close();
  }
});

test('save to folder writes the golden files', async () => {
  const data = tmp('calib3d-app-'), out = tmp('calib3d-out-');
  const { app, win } = await launch(data);
  try {
    await app.evaluate(({ dialog }, dir) => { dialog.showOpenDialog = async () => ({ canceled: false, filePaths: [dir] }); }, out);
    await win.selectOption('#lang', 'ru');
    await win.waitForFunction(() => window.calib3dApp.done());
    await win.evaluate(() => window.calib3dApp.go(3));
    await win.click('#save-folder');
    await expect(win.locator('#download-status')).toContainText('10');
    const names = fs.readdirSync(out).sort();
    expect(names.length).toBe(10);
    const gold = fs.readFileSync(path.join(ROOT, 'tests', 'golden', 'ECC_0.4_Flow_PETG_80-120.gcode'), 'utf8').split('\n');
    const ours = fs.readFileSync(path.join(out, 'ECC_0.4_Flow_PETG_80-120.gcode'), 'utf8').split('\n');
    expect(ours.filter((l, i) => l !== gold[i]).length).toBe(1);
  } finally {
    await app.close();
  }
});

test('save as zip', async () => {
  const data = tmp('calib3d-app-'), out = tmp('calib3d-out-');
  const file = path.join(out, 'all.zip');
  const { app, win } = await launch(data);
  try {
    await app.evaluate(({ dialog }, f) => { dialog.showSaveDialog = async () => ({ canceled: false, filePath: f }); }, file);
    await win.evaluate(() => window.calib3dApp.go(3));
    await win.click('#save-zip');
    await expect(win.locator('#download-status')).toContainText('all.zip');
    const buf = fs.readFileSync(file);
    expect(buf.readUInt32LE(0)).toBe(0x04034b50);
    expect(buf.length).toBeGreaterThan(100000);
  } finally {
    await app.close();
  }
});

test('no permission is ever granted (pointer lock included)', async () => {
  // main.js answers every permission request with "no"; checked in the source and in the page
  const src = fs.readFileSync(path.join(ROOT, 'electron', 'main.js'), 'utf8');
  expect(src).toMatch(/setPermissionRequestHandler\(\(_wc, _permission, cb\) => cb\(false\)\)/);
  const data = tmp('calib3d-app-');
  const { app, win } = await launch(data);
  try {
    expect(await win.evaluate(() => document.pointerLockElement)).toBe(null);
  } finally {
    await app.close();
  }
});

test('window place: window-state.js decides, test mode writes nothing', async () => {
  const data = tmp('calib3d-app-');
  fs.writeFileSync(path.join(data, 'window-state.json'), JSON.stringify({ x: 100, y: 80, width: 1000, height: 700, maximized: false }));
  const { app } = await launch(data);
  try {
    const size = await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].getSize());
    expect(size[0]).toBeGreaterThanOrEqual(900);
  } finally {
    await app.close();
  }
  const saved = JSON.parse(fs.readFileSync(path.join(data, 'window-state.json'), 'utf8'));
  expect(saved).toEqual({ x: 100, y: 80, width: 1000, height: 700, maximized: false });
});

const BUILT = path.join(ROOT, 'dist', 'electron', 'win-unpacked', 'Calibrate 3D Printer.exe');
test('the built app (dist/electron) starts and generates', async () => {
  test.skip(!fs.existsSync(BUILT), 'no build in dist/electron');
  const data = tmp('calib3d-built-');
  const app = await electron.launch({ executablePath: BUILT, args: ['--user-data-dir=' + data],
    env: Object.assign({}, process.env, { CALIB3D_TEST: '1' }) });
  try {
    const win = await app.firstWindow();
    await win.waitForFunction(() => window.calib3dApp && window.calib3dApp.done(), null, { timeout: 60000 });
    const ok = await win.evaluate(() => Object.values(window.calib3dApp.state.results).every((r) => r.ok && !r.problems.length));
    expect(ok).toBe(true);
    expect(await app.evaluate(({ BrowserWindow }) => BrowserWindow.getAllWindows()[0].isVisible())).toBe(false);
  } finally {
    await app.close();
  }
});
