// Profiles and the schema check - twin of python/calib3d/core/profiles.py.
(function () {
  'use strict';
  const root = typeof globalThis !== 'undefined' ? globalThis : window;
  const C3D = root.C3D || (root.C3D = {});
  const isNode = typeof module === 'object' && module.exports;
  if (isNode) require('./data.js');

  const clone = (x) => JSON.parse(JSON.stringify(x));
  const D = () => C3D.data;

  function printers() { return clone(D().printers); }
  function materials() { return clone(D().materials); }
  function firmware() { return clone(D().firmware); }
  function schema() { return D().schema; }
  function version() { return D().version; }

  function printer(id) {
    const p = D().printers.find((x) => x.id === id);
    if (!p) throw new Error('no printer ' + id);
    return clone(p);
  }

  function material(id) {
    const m = D().materials.find((x) => x.id === id);
    if (!m) throw new Error('no material ' + id);
    return clone(m);
  }

  function getPath(d, path) {
    let cur = d;
    for (const part of path.split('.')) {
      if (cur === null || typeof cur !== 'object' || Array.isArray(cur) || !(part in cur)) return [null, false];
      cur = cur[part];
    }
    return [cur, true];
  }

  const isNum = (v) => typeof v === 'number' && Number.isFinite(v);
  const isObj = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);

  function repr(v) { return v === undefined ? 'null' : JSON.stringify(v); }

  function checkField(d, spec, errors, required) {
    const path = spec[0], kind = spec[1];
    const [v, present] = getPath(d, path);
    if (!present) {
      if (required) errors.push(path + ': missing');
      return;
    }
    let ok;
    if (kind === 'str') ok = typeof v === 'string' && v.trim() !== '';
    else if (kind === 'bool') ok = typeof v === 'boolean';
    else if (kind === 'num' || kind === 'int') {
      ok = isNum(v) && (kind === 'num' || Number.isInteger(v));
      if (ok && spec.length > 2 && !(spec[2] <= v && v <= spec[3])) {
        errors.push(`${path}: ${v} outside ${spec[2]}..${spec[3]}`);
        return;
      }
    } else if (kind === 'enum') ok = spec[2].indexOf(v) >= 0;
    else if (kind === 'lines') ok = Array.isArray(v) && v.length > 0 && v.every((s) => typeof s === 'string');
    else if (kind === 'list') ok = Array.isArray(v) && v.length === 2 && v.every((x) => isNum(x) && spec[2] <= x && x <= spec[3]) && v[0] < v[1];
    else if (kind === 'flags') ok = isObj(v) && Object.values(v).every((x) => typeof x === 'boolean');
    else if (kind === 'state') ok = isObj(v) && ['x', 'y', 'z', 'e', 'time'].every((k) => isNum(v[k]));
    else if (kind === 'overrides') ok = isObj(v) && Object.values(v).every((x) => typeof x === 'string' || Array.isArray(x) || x === null);
    else ok = false;
    if (!ok) errors.push(`${path}: bad value ${repr(v)}`);
  }

  function validatePrinter(p) {
    const errors = [];
    if (!isObj(p)) return ['not an object'];
    for (const spec of schema().printer) checkField(p, spec, errors, true);
    for (const spec of schema().printer_optional) checkField(p, spec, errors, false);
    if (!errors.length && p.default_accel > p.max_accel) errors.push('default_accel: above max_accel');
    if (!errors.length && p.bed.shape === 'round' && p.bed.origin !== 'center') errors.push('bed.origin: a round bed has its origin in the centre');
    return errors;
  }

  function validateMaterial(m) {
    const errors = [];
    if (!isObj(m)) return ['not an object'];
    for (const spec of schema().material) checkField(m, spec, errors, true);
    if (!errors.length) {
      const t = m.tower;
      if (t.start === t.end) errors.push('tower: start equals end');
      else if (Math.abs(t.start - t.end) / t.step > 15) errors.push('tower: more than 16 levels');
    }
    return errors;
  }

  // JavaScript has no int/float, nothing to normalise; kept for symmetry with Python.
  function normalizePrinter(p) { return clone(p); }
  function normalizeMaterial(m) { return clone(m); }

  const api = { printers, materials, firmware, schema, version, printer, material, validatePrinter,
    validateMaterial, normalizePrinter, normalizeMaterial, clone };
  C3D.profiles = api;
  if (isNode) module.exports = api;
})();
