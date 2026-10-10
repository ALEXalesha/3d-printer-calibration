// Laws from the independent review before 1.0.0, the JavaScript side (Python: test_release_review.py).
'use strict';
const test = require('node:test');
const assert = require('node:assert');
const C3D = require('./helpers');

const G = C3D.generator;
const P = C3D.profiles;

test('a round bed parks at its front, inside the circle', () => {
  const [x, y] = G.parkPoint({ x: 200, y: 200, origin: 'center', shape: 'round' });
  assert.ok(Math.hypot(x, y) <= 100 - 5, `${x} ${y}`);
  const text = G.generate(P.printer('generic-delta-klipper'), P.material('pla'), 'cube').text;
  assert.ok(!/X-95 Y95/.test(text));
});

test('invalid parameters are refused', () => {
  assert.throws(() => G.generate(P.printer('elegoo-centauri-carbon'), P.material('petg'), 'flow', { f_start: 120, f_step: 10 }),
    (e) => e.kind === 'params');
  assert.throws(() => G.generate(P.printer('generic-klipper'), P.material('pla'), 'temp_tower', { t_start: NaN }),
    (e) => e.kind === 'params');
});

test('file names carry only characters every disk takes', () => {
  const p = Object.assign(P.printer('generic-klipper'), { prefix: 'my/printer:"1"?' });
  const r = G.generate(p, P.material('pla'), 'cube');
  assert.match(r.name, /^[A-Za-z0-9._+-]+\.gcode$/);
});
