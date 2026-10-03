// Runs cases from a JSON file through the JavaScript core and prints the results as JSON.
// Used by tests/py/test_equality.py, which runs the same cases through the Python core.
//   node tests/js/equality_runner.js cases.json > results.json
'use strict';
const fs = require('fs');
const crypto = require('crypto');
const C3D = require('./helpers');

const cases = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const sha = (s) => crypto.createHash('sha256').update(s, 'utf8').digest('hex');
const out = [];
for (const c of cases) {
  try {
    if (c.kind === 'gen') {
      const r = C3D.generator.generate(c.printer, c.material, c.test, c.params, c.lang);
      const row = { name: r.name, sha: sha(r.text), lines: r.g.lines.length, summary: C3D.params.summary(r) };
      if (c.check) row.problems = C3D.check.checkResult(r, c.test);
      if (c.preview) {
        const p = C3D.preview.previewData(r);
        const sum = (list) => list.reduce((a, s) => a + s[0] + 2 * s[1] + 3 * s[2] + 4 * s[3], 0);
        row.preview = [p.top.length, p.front ? p.front.length : -1, C3D.num.fixed(sum(p.top), 3), p.front ? C3D.num.fixed(sum(p.front), 3) : ''];
      }
      out.push(row);
    } else if (c.kind === 'check') {
      out.push({ problems: C3D.check.check(c.text, c.printer, c.material, c.test, c.body_start, c.body_end, c.max_z) });
    } else if (c.kind === 'import') {
      out.push(C3D.importer.parse(c.text, c.file));
    } else if (c.kind === 'helper') {
      out.push(C3D.params.helper(c.test, c.text, c.printer, c.material, c.params));
    } else if (c.kind === 'validate') {
      out.push({ errors: C3D.params.validate(c.test, c.params, c.printer, c.material),
        printer: C3D.profiles.validatePrinter(c.printer), material: C3D.profiles.validateMaterial(c.material) });
    } else if (c.kind === 'num') {
      out.push({ fixed: c.values.map(([x, d]) => C3D.num.fixed(x, d)), round: c.values.map(([x]) => C3D.num.pyRound(x)),
        repr: c.values.map(([x]) => C3D.num.pyRepr(x)), hypot: c.pairs.map(([a, b]) => C3D.num.hypot(a, b)) });
    }
  } catch (e) {
    out.push({ error: e.kind || e.message });
  }
}
process.stdout.write(JSON.stringify(out));
