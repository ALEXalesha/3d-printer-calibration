// web/js/core/data.js must be the bundle of the current profiles/*.json (tools/build_data.py).
'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const C3D = require('./helpers');

const ROOT = path.join(__dirname, '..', '..');
const read = (p) => JSON.parse(fs.readFileSync(p, 'utf8'));
const dir = (d) => fs.readdirSync(path.join(ROOT, 'profiles', d)).filter((f) => f.endsWith('.json')).sort()
  .map((f) => read(path.join(ROOT, 'profiles', d, f)));

test('data.js is up to date with profiles/ (run python tools/build_data.py)', () => {
  const order = ['pla', 'petg', 'abs', 'asa', 'tpu'];
  const mats = dir('materials').sort((a, b) => (order.indexOf(a.id) < 0 ? 99 : order.indexOf(a.id)) - (order.indexOf(b.id) < 0 ? 99 : order.indexOf(b.id)));
  const printers = dir('printers').sort((a, b) => {
    const ka = [!a.verified, a.name.toLowerCase()], kb = [!b.verified, b.name.toLowerCase()];
    return ka[0] - kb[0] || (ka[1] < kb[1] ? -1 : ka[1] > kb[1] ? 1 : 0);
  });
  const expect = {
    version: fs.readFileSync(path.join(ROOT, 'VERSION'), 'utf8').trim(),
    printers, materials: mats,
    firmware: read(path.join(ROOT, 'profiles', 'firmware.json')),
    schema: read(path.join(ROOT, 'profiles', 'schema.json')),
    tables: read(path.join(ROOT, 'profiles', 'tables.json')),
    gcode_text: read(path.join(ROOT, 'profiles', 'gcode_text.json')),
    tests: read(path.join(ROOT, 'profiles', 'tests.json')).tests,
    ui_text: read(path.join(ROOT, 'profiles', 'ui_text.json')),
  };
  assert.deepStrictEqual(C3D.data, expect);
});

test('package.json version = VERSION', () => {
  assert.strictEqual(read(path.join(ROOT, 'package.json')).version, C3D.data.version);
});
