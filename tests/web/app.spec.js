// The page in headless Chromium: the wizard, import, previews, downloads, the helper.
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const { test, expect, open, waitDone, ROOT } = require('./fixtures');

const GOLDEN = path.join(ROOT, 'tests', 'golden');
const SAMPLES = path.join(ROOT, 'tests', 'import');

function readZip(buf) {
  // central directory -> {name: text}
  const out = {};
  let end = buf.length - 22;
  while (buf.readUInt32LE(end) !== 0x06054b50) end--;
  const count = buf.readUInt16LE(end + 10);
  let at = buf.readUInt32LE(end + 16);
  for (let i = 0; i < count; i++) {
    const method = buf.readUInt16LE(at + 10);
    const size = buf.readUInt32LE(at + 20);
    const nameLen = buf.readUInt16LE(at + 28), extra = buf.readUInt16LE(at + 30), comment = buf.readUInt16LE(at + 32);
    const local = buf.readUInt32LE(at + 42);
    const name = buf.slice(at + 46, at + 46 + nameLen).toString('utf8');
    const lNameLen = buf.readUInt16LE(local + 26), lExtra = buf.readUInt16LE(local + 28);
    const data = buf.slice(local + 30 + lNameLen + lExtra, local + 30 + lNameLen + lExtra + size);
    out[name] = (method === 8 ? zlib.inflateRawSync(data) : data).toString('utf8');
    at += 46 + nameLen + extra + comment;
  }
  return out;
}

test('loads without errors and generates all ten tests', async ({ page }) => {
  await open(page);
  const st = await page.evaluate(() => {
    const S = window.calib3dApp.state;
    return Object.entries(S.results).map(([k, v]) => [k, v.ok, v.ok ? v.problems.length : -1, v.ok ? v.summary.name : '']);
  });
  expect(st.length).toBe(10);
  for (const [tid, ok, problems] of st) {
    expect(ok, tid).toBe(true);
    expect(problems, tid).toBe(0);
  }
  expect(st.map((r) => r[3])).toContain('ECC_0.4_TempTower_PETG_260-220.gcode');
  expect(page.errors).toEqual([]);
});

test('the page gives the golden bytes (line 2 aside)', async ({ page }) => {
  await open(page);
  await page.selectOption('#lang', 'ru');     // G-code comments follow the interface language
  await waitDone(page);
  for (const tid of ['cube', 'pressure_advance']) {
    const r = await page.evaluate((tid) => {
      const o = window.calib3dApp.state.results[tid];
      return { name: o.summary.name, text: o.res.text };
    }, tid);
    const gold = fs.readFileSync(path.join(GOLDEN, r.name), 'utf8').split('\n');
    const ours = r.text.split('\n');
    expect(ours.length).toBe(gold.length);
    const diff = gold.map((l, i) => (l === ours[i] ? -1 : i)).filter((i) => i >= 0);
    expect(diff).toEqual([1]);
  }
});

test('steps, back and next', async ({ page }) => {
  await open(page);
  await expect(page.locator('#page-printer')).toBeVisible();
  await page.click('#next');
  await expect(page.locator('#page-material')).toBeVisible();
  await expect(page.locator('#page-printer')).toBeHidden();
  await page.click('.step[data-step="4"]');
  await expect(page.locator('#page-results')).toBeVisible();
  await expect(page.locator('.step[data-step="4"]')).toHaveAttribute('aria-selected', 'true');
  await page.click('#back');
  await expect(page.locator('#page-download')).toBeVisible();
  await expect(page.locator('#next')).toBeHidden();
});

test('theme and language switch and survive a reload', async ({ page }) => {
  await open(page);
  await page.selectOption('#theme', 'light');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await page.selectOption('#lang', 'en');
  await expect(page.locator('#title')).toHaveText('Calibrate 3D Printer');
  await waitDone(page);
  await page.reload();
  await waitDone(page);
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await expect(page.locator('.step[data-step="0"]')).toHaveText('1. Printer');
  const title = await page.evaluate(() => window.calib3dApp.state.results.temp_tower.res.text.split('\n')[1]);
  expect(title).toContain('Temperature tower PETG 260-220');
  await page.selectOption('#theme', 'glass');
  await expect(page.locator('html')).not.toHaveAttribute('data-theme', /./);
});

test('import a slicer G-code: profile filled, report shown', async ({ page }) => {
  await open(page);
  await page.setInputFiles('#gcode-file', path.join(SAMPLES, 'orca.gcode'));
  await expect(page.locator('#import-report')).toBeVisible();
  await expect(page.locator('#import-report')).toContainText('PRINT_START');
  await waitDone(page);
  const s = await page.evaluate(() => {
    const S = window.calib3dApp.state;
    return { id: S.printer.id, x: S.printer.bed.x, first: S.material.first_layer_temp, cube: S.results.cube.res.text, problems: S.results.cube.problems };
  });
  expect(s).toMatchObject({ id: 'imported', x: 300, first: 215, problems: [] });
  expect(s.cube).toContain('PRINT_START BED=60 HOTEND=215');
  await expect(page.locator('#f-bed-x')).toHaveValue('300');
});

test('import marks what was not found', async ({ page }) => {
  await open(page);
  await page.setInputFiles('#gcode-file', path.join(SAMPLES, 'cura.gcode'));
  await expect(page.locator('#f-bed-x')).toHaveClass(/missing/);
  await expect(page.locator('#f-nozzle')).toHaveClass(/missing/);
  await page.fill('#f-bed-x', '230');
  await page.locator('#f-bed-x').dispatchEvent('change');
  await expect(page.locator('#f-bed-x')).not.toHaveClass(/missing/);
});

test('a parameter change renames and regenerates', async ({ page }) => {
  await open(page);
  await page.click('.step[data-step="2"]');
  await page.click('#test-list li[data-test="temp_tower"] .name');
  await page.fill('#p-t_end', '240');
  await page.locator('#p-t_end').dispatchEvent('change');
  await page.waitForFunction(() => {
    const o = window.calib3dApp.state.results.temp_tower;
    return o && o.ok && o.summary.name.endsWith('260-240.gcode');
  });
  await page.fill('#p-t_end', '260');
  await page.locator('#p-t_end').dispatchEvent('change');
  await expect(page.locator('#param-error')).toContainText('t_end');
});

test('previews are drawn: top, front and 3D', async ({ page }) => {
  await open(page);
  await page.click('.step[data-step="2"]');
  await page.click('#test-list li[data-test="temp_tower"] .name');
  await page.waitForTimeout(300);
  const colored = async (sel) => page.evaluate((sel) => {
    const c = document.querySelector(sel);
    const g = c.getContext('2d');
    const d = g.getImageData(0, 0, c.width, c.height).data;
    let n = 0;
    for (let i = 0; i < d.length; i += 4) if (d[i] > 200 && d[i + 1] < 90) n++;   // red labels
    return n;
  }, sel);
  expect(await colored('#view-top')).toBeGreaterThan(5);
  expect(await colored('#view-front')).toBeGreaterThan(50);
  const has3d = await page.evaluate(() => !!document.querySelector('#view-3d canvas'));
  expect(has3d).toBe(true);
  await page.locator('#layer-slider').fill('10');
  await expect(page.locator('#layer-value')).toContainText('10 /');
});

test('download all as zip: the same files as the core', async ({ page }) => {
  await open(page);
  await page.selectOption('#lang', 'ru');
  await waitDone(page);
  await page.click('.step[data-step="3"]');
  const [dl] = await Promise.all([page.waitForEvent('download'), page.click('#download-zip')]);
  expect(dl.suggestedFilename()).toBe('ECC_PETG_calibration.zip');
  const files = readZip(fs.readFileSync(await dl.path()));
  expect(Object.keys(files).length).toBe(10);
  const gold = fs.readFileSync(path.join(GOLDEN, 'ECC_0.4_Cube20_PETG.gcode'), 'utf8').split('\n');
  const ours = files['ECC_0.4_Cube20_PETG.gcode'].split('\n');
  expect(ours.filter((l, i) => l !== gold[i]).length).toBe(1);
});

test('one file download and unchecked tests left out', async ({ page }) => {
  await open(page);
  await page.click('.step[data-step="2"]');
  await page.click('#select-none');
  await page.check('#test-list input[data-test="flow"]');
  await page.click('.step[data-step="3"]');
  await expect(page.locator('#order tbody tr')).toHaveCount(1);
  const [dl] = await Promise.all([page.waitForEvent('download'), page.click('[data-download="flow"]')]);
  expect(dl.suggestedFilename()).toBe('ECC_0.4_Flow_PETG_80-120.gcode');
});

test('result helper', async ({ page }) => {
  await open(page);
  await page.click('.step[data-step="4"]');
  await page.fill('[data-helper-in="pressure_advance"]', '024');
  await expect(page.locator('[data-helper-out="pressure_advance"]')).toContainText('0.024');
  await page.fill('[data-helper-in="cube"]', '19.7 19.7 19.9');
  await expect(page.locator('[data-helper-out="cube"]')).toContainText('1.015');
});

test('own printer profile: save, survives reload, delete', async ({ page }) => {
  await open(page);
  await page.fill('#f-name', 'My CC');
  await page.locator('#f-name').dispatchEvent('change');
  await page.click('#save-printer');
  await expect(page.locator('#printer-select')).toHaveValue('my-my-cc');
  await page.reload();
  await waitDone(page);
  await expect(page.locator('#printer-select')).toHaveValue('my-my-cc');
  await page.click('#delete-printer');
  await expect(page.locator('#printer-select')).toHaveValue('elegoo-centauri-carbon');
});

test('profile JSON export and import', async ({ page }, info) => {
  await open(page);
  const [dl] = await Promise.all([page.waitForEvent('download'), page.click('#export-json')]);
  const file = info.outputPath('p.json');
  await dl.saveAs(file);
  const data = JSON.parse(fs.readFileSync(file, 'utf8'));
  expect(data.id).toBe('elegoo-centauri-carbon');
  data.name = 'From JSON';
  fs.writeFileSync(file, JSON.stringify(data));
  await page.setInputFiles('input[accept=".json,application/json"]', file);
  await expect(page.locator('#printer-select')).toHaveValue('my-from-json');
});

test('invalid profile value is reported', async ({ page }) => {
  await open(page);
  await page.fill('#f-default_accel', '30000');
  await page.locator('#f-default_accel').dispatchEvent('change');
  await expect(page.locator('#printer-status')).toContainText('default_accel');
});

test('narrow window: no horizontal scroll', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 });
  await open(page);
  for (let i = 0; i < 5; i++) {
    await page.evaluate((i) => window.calib3dApp.go(i), i);
    const wide = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(wide, 'step ' + i).toBeLessThanOrEqual(1);
  }
});

test('ids are unique and every field has a label', async ({ page }) => {
  await open(page);
  const r = await page.evaluate(() => {
    const ids = [...document.querySelectorAll('[id]')].map((e) => e.id);
    const dup = ids.filter((id, i) => ids.indexOf(id) !== i);
    const unlabeled = [...document.querySelectorAll('input:not([type=file]):not([type=checkbox]), select, textarea')]
      .filter((e) => !e.labels.length && !e.getAttribute('aria-label') && !e.closest('label')).map((e) => e.id || e.outerHTML.slice(0, 60));
    return { dup, unlabeled };
  });
  expect(r.dup).toEqual([]);
  expect(r.unlabeled).toEqual([]);
});

test('buttons and text readable in every theme', async ({ page }) => {
  await open(page);
  for (const theme of ['glass', 'formal', 'light', 'night', 'warm']) {
    await page.selectOption('#theme', theme);
    const r = await page.evaluate(() => {
      const rgb = (s) => (s.match(/[\d.]+/g) || []).slice(0, 3).map(Number);
      const lum = (c) => {
        const v = c.map((x) => x / 255).map((x) => (x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4));
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
      };
      const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
      const out = {};
      for (const sel of ['#next', '#import-button']) {
        const st = getComputedStyle(document.querySelector(sel));
        out[sel] = ratio(rgb(st.color), rgb(st.backgroundColor));
      }
      return out;
    });
    for (const [sel, v] of Object.entries(r)) expect(v, `${theme} ${sel}`).toBeGreaterThan(2.9);
  }
});

// Alexey 03.10 (screenshots 231818/231900/231903): "Тема" stuck to its list, the text sat close
// to the arrow, and the open list was a plain white system list in every theme.
test('header lists: room around the text, themed options', async ({ page }) => {
  await open(page);
  const geo = await page.evaluate(() => {
    const out = [];
    for (const id of ['theme', 'lang']) {
      const sel = document.getElementById(id), lab = document.getElementById(id + '-label');
      const cs = getComputedStyle(sel);
      out.push({ id, gap: sel.getBoundingClientRect().left - lab.getBoundingClientRect().right,
        padR: parseFloat(cs.paddingRight), padL: parseFloat(cs.paddingLeft) });
    }
    const t = document.getElementById('theme').getBoundingClientRect(), l = document.getElementById('lang-label').getBoundingClientRect();
    return { out, pairGap: l.left - t.right };
  });
  for (const g of geo.out) {
    expect(g.gap, g.id).toBeGreaterThanOrEqual(8);
    expect(g.padR, g.id).toBeGreaterThanOrEqual(28);
    expect(g.padL, g.id).toBeGreaterThanOrEqual(12);
  }
  expect(geo.pairGap).toBeGreaterThanOrEqual(16);
  for (const th of ['glass', 'night']) {
    await page.selectOption('#theme', th);
    const bg = await page.evaluate(() => getComputedStyle(document.querySelector('#theme option')).backgroundColor);
    expect(bg, th).not.toBe('rgb(255, 255, 255)');
  }
});
