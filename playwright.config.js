// Browser tests of the page (version A): headless Chromium only, one worker, output in TEMP.
const os = require('os');
const path = require('path');
const { defineConfig } = require('@playwright/test');

module.exports = defineConfig({
  testDir: './tests/web',
  workers: 1,
  fullyParallel: false,
  timeout: 90000,
  reporter: [['list']],
  outputDir: path.join(os.tmpdir(), 'calib3d-playwright'),
  use: {
    headless: true,
    viewport: { width: 1280, height: 860 },
    acceptDownloads: true,
  },
});
