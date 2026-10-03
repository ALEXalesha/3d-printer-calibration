// num.js against values printed by CPython (tests/js/num_vectors.json, made by Python).
'use strict';
const test = require('node:test');
const assert = require('node:assert');
const V = require('./num_vectors.json');
const C3D = require('./helpers');
const N = C3D.num;

test('fixed = Python format, exact halves to even', () => {
  for (const [x, d, s] of V.fixed) assert.strictEqual(N.fixed(x, d), s, `${x} ${d}`);
});
test('pyRound = Python round()', () => {
  for (const [x, r] of V.round) assert.strictEqual(N.pyRound(x), r, String(x));
});
test('hypot = math.hypot bit for bit', () => {
  for (const [a, b, h] of V.hypot) assert.strictEqual(N.hypot(a, b), h, `${a} ${b}`);
});
test('pyRepr = repr(float)', () => {
  for (const [x, s] of V.repr) assert.strictEqual(N.pyRepr(x), s, String(x));
});
test('tan table', () => {
  assert.strictEqual(N.tanDeg(45), 0.9999999999999999);
  assert.strictEqual(N.tanDeg(0), 0);
});
