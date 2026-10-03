// Screenshots of the page in headless Chromium: every step, light and glass (dark), RU and EN.
//   node tools/screens_web.js <out dir>
// Pointer lock is stubbed; nothing appears on the screen.
'use strict';
const path = require('path');
const fs = require('fs');
const { chromium } = require('playwright-core');

const ROOT = path.join(__dirname, '..');
const URL = 'file:///' + path.join(ROOT, 'web', 'index.html').split(path.sep).join('/');
const STEPS = ['printer', 'material', 'tests', 'download', 'results'];

(async () => {
  const out = process.argv[2] || path.join(ROOT, 'local', 'shots');
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1280, height: 860 } });
  await page.addInitScript(() => {
    Element.prototype.requestPointerLock = function () {};
    document.exitPointerLock = function () {};
  });
  await page.goto(URL);
  await page.evaluate(() => localStorage.clear());
  for (const lang of ['ru', 'en']) {
    for (const theme of ['light', 'glass']) {
      await page.evaluate(([lang, theme]) => {
        localStorage.setItem('calib3d-settings', JSON.stringify({ lang }));
        localStorage.setItem('calib3d-theme', JSON.stringify(theme));
      }, [lang, theme]);
      await page.reload();
      await page.waitForFunction(() => window.calib3dApp && window.calib3dApp.done(), null, { timeout: 60000 });
      for (let i = 0; i < STEPS.length; i++) {
        await page.evaluate((i) => window.calib3dApp.go(i), i);
        if (STEPS[i] === 'tests') await page.click('#test-list li[data-test="temp_tower"] .name');
        if (STEPS[i] === 'results') {
          await page.fill('[data-helper-in="pressure_advance"]', '024');
          await page.fill('[data-helper-in="flow"]', '104');
        }
        await page.waitForTimeout(250);
        const file = path.join(out, `web_${theme}_${lang}_${i + 1}_${STEPS[i]}.png`);
        await page.screenshot({ path: file });
        console.log(file);
      }
    }
  }
  await browser.close();
})();
