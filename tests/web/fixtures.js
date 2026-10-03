// Shared setup: the page from a file URL, pointer lock replaced by a stub in every frame
// (headless Chromium on Windows would otherwise clip the real mouse cursor), console
// errors collected.
const path = require('path');
const { test: base, expect } = require('@playwright/test');

const ROOT = path.join(__dirname, '..', '..');
const URL = 'file:///' + path.join(ROOT, 'web', 'index.html').split(path.sep).join('/');

const test = base.extend({
  page: async ({ page }, use) => {
    await page.addInitScript(() => {
      window.__pointerLockCalls = 0;
      Element.prototype.requestPointerLock = function () { window.__pointerLockCalls += 1; return Promise.resolve(); };
      document.exitPointerLock = function () {};
    });
    page.errors = [];
    page.on('pageerror', (e) => page.errors.push(String(e)));
    page.on('console', (m) => { if (m.type() === 'error') page.errors.push(m.text()); });
    await use(page);
    expect(await page.evaluate(() => window.__pointerLockCalls || 0)).toBe(0);
  },
});

async function open(page, opts) {
  await page.goto(URL);
  if (!opts || opts.clear !== false) {
    await page.evaluate(() => localStorage.clear());
    await page.reload();
  }
  await page.waitForFunction(() => window.calib3dApp && window.calib3dApp.done(), null, { timeout: 60000 });
}

async function waitDone(page) {
  await page.waitForFunction(() => window.calib3dApp.done(), null, { timeout: 60000 });
}

module.exports = { test, expect, open, waitDone, ROOT, URL };
