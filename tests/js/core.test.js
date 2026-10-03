// The JavaScript core on its own: profiles, check, import samples (shared expectations).
'use strict';
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const C3D = require('./helpers');

const G = C3D.generator, P = C3D.profiles;

test('all bundled profiles valid', () => {
  for (const p of P.printers()) assert.deepStrictEqual(P.validatePrinter(p), [], p.id);
  for (const m of P.materials()) assert.deepStrictEqual(P.validateMaterial(m), [], m.id);
});

test('every printer x test passes the check', () => {
  const mats = P.materials();
  P.printers().forEach((p, i) => {
    G.TEST_IDS.forEach((tid, k) => {
      const r = G.generate(p, mats[(i + k) % mats.length], tid);
      assert.deepStrictEqual(C3D.check.checkResult(r, tid), [], `${p.id} ${tid}`);
      assert.ok(!/\{[^{}\n]*\}/.test(r.text), `${p.id} ${tid} braces`);
    });
  });
});

test('check catches injected faults', () => {
  const r = G.generate(P.printer('elegoo-centauri-carbon'), P.material('petg'), 'cube');
  const lines = r.text.split('\n');
  const codes = (text) => C3D.check.check(text, r.g.ctx.p, r.g.ctx.m, 'cube', r.g.body_start, r.g.body_end, r.max_z).map((s) => s.split(':')[0]);
  const at = r.g.body_start + 40;
  const edit = (line) => { const ls = lines.slice(); ls[at] = line; return ls.join('\n'); };
  assert.ok(codes(edit('M900 K0.1')).includes('foreign_command'));
  assert.ok(codes(edit('G1 X300.000 Y10.000 E0.5 F3000')).includes('outside_bed'));
  assert.ok(codes(edit('M104 S400')).includes('temperature'));
  assert.ok(codes(edit('M140 S{bed_temp}')).includes('placeholder'));
});

test('canvas and wipe are options', () => {
  const cc = P.printer('elegoo-centauri-carbon');
  cc.options.canvas = false;
  const t = G.generate(cc, P.material('pla'), 'first_layer').text;
  assert.ok(!t.includes('M6211') && t.includes('M729'));
});

const DIR = path.join(__dirname, '..', 'import');
const EXPECTED = JSON.parse(fs.readFileSync(path.join(DIR, 'expected.json'), 'utf8'));
function subset(want, got, where) {
  for (const [k, v] of Object.entries(want)) {
    assert.ok(k in got, `${where}${k} not found`);
    if (v && typeof v === 'object' && !Array.isArray(v)) subset(v, got[k], where + k + '.');
    else assert.deepStrictEqual(got[k], v, where + k);
  }
}
for (const [name, exp] of Object.entries(EXPECTED)) {
  if (name.startsWith('_')) continue;
  test('import ' + name, () => {
    const r = C3D.importer.parse(fs.readFileSync(path.join(DIR, name), 'utf8'), name);
    assert.strictEqual(r.slicer, exp.slicer);
    assert.strictEqual(r.firmware_from, exp.firmware_from);
    assert.deepStrictEqual(r.warnings, exp.warnings);
    subset(exp.printer, r.printer, 'printer.');
    subset(exp.material, r.material, 'material.');
    assert.deepStrictEqual(r.missing, exp.missing);
    for (const l of exp.start) assert.ok(r.start_gcode.includes(l), l);
    for (const l of exp.start_absent) assert.ok(!r.start_gcode.includes(l), l);
    for (const l of exp.end) assert.ok(r.end_gcode.includes(l), l);
    assert.strictEqual(r.replaced.length, exp.replaced);
  });
}

test('helper', () => {
  const m = P.material('petg'), cc = P.printer('elegoo-centauri-carbon');
  assert.strictEqual(C3D.params.helper('pressure_advance', '024', cc, m, {}).value, '0.024');
  assert.strictEqual(C3D.params.helper('flow', '104', cc, P.material('pla'), {}).value, '1.019');
});
