// electron/window-state.js is the shared module of Alexey's Electron apps (calculators,
// Paint Pro, ...): byte for byte the same file, and its rule holds on random inputs.
'use strict';
const test = require('node:test');
const assert = require('node:assert');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const fc = require('fast-check');
const WS = require('../../electron/window-state.js');

const SHARED_SHA256 = 'f9114de787431b1c85a057b4e9038a4e7c75dd12e80f3af44230309f1fb54790';

test('the shared module, unchanged', () => {
  const text = fs.readFileSync(path.join(__dirname, '..', '..', 'electron', 'window-state.js'));
  assert.strictEqual(crypto.createHash('sha256').update(text).digest('hex'), SHARED_SHA256);
});

const OPTS = { width: 1180, height: 820, minWidth: 900, minHeight: 620 };
const SCREEN = [{ x: 0, y: 0, width: 1920, height: 1040 }];

test('garbage gives the default', () => {
  for (const bad of [null, 'x', 5, [], { width: 'a' }]) assert.deepStrictEqual(WS.restore(bad, SCREEN, OPTS), { width: 1180, height: 820, maximized: false });
});

test('the title bar stays reachable', () => {
  fc.assert(fc.property(fc.integer({ min: -4000, max: 4000 }), fc.integer({ min: -4000, max: 4000 }),
    fc.integer({ min: 100, max: 5000 }), fc.integer({ min: 100, max: 4000 }), (x, y, w, h) => {
      const r = WS.restore({ x, y, width: w, height: h }, SCREEN, OPTS);
      if (r.x === undefined) return true;
      return r.x >= 0 && r.x + 80 <= 1920 && r.y >= 0 && r.y <= 1040 - 38;
    }), { numRuns: 400 });
});
