// Test parameters and the result helper - twin of python/calib3d/core/params.py.
(function () {
  'use strict';
  const root = typeof globalThis !== 'undefined' ? globalThis : window;
  const C3D = root.C3D || (root.C3D = {});
  const isNode = typeof module === 'object' && module.exports;
  if (isNode) { require('./data.js'); require('./num.js'); }
  const { fixed, pyRound, trim } = C3D.num;

  function tests() { return C3D.data.tests; }

  function testInfo(id) {
    const t = tests().find((x) => x.id === id);
    if (!t) throw new Error('no test ' + id);
    return t;
  }

  function normalize(testId, prm) { return Object.assign({}, prm); }

  const isNum = (v) => typeof v === 'number' && Number.isFinite(v);

  function validate(testId, prm, printer, material) {
    const errors = [];
    for (const spec of testInfo(testId).params) {
      const k = spec.key;
      if (!(k in prm)) { errors.push(`${k}: missing`); continue; }
      const v = prm[k];
      if (spec.type === 'list') {
        if (!Array.isArray(v) || v.length < 2 || v.length > 8) { errors.push(`${k}: 2..8 values`); continue; }
        if (v.some((x) => !isNum(x) || !(spec.min <= x && x <= spec.max))) errors.push(`${k}: values ${trim(spec.min, 3)}..${trim(spec.max, 3)}`);
        else if (v.some((b, i) => i > 0 && b <= v[i - 1])) errors.push(`${k}: must grow`);
        continue;
      }
      if (!isNum(v)) { errors.push(`${k}: not a number`); continue; }
      if (spec.type === 'int' && !Number.isInteger(v)) errors.push(`${k}: whole number`);
      if (!(spec.min <= v && v <= spec.max)) errors.push(`${k}: ${trim(spec.min, 3)}..${trim(spec.max, 3)}`);
    }
    if (errors.length) return errors;
    if (testId === 'temp_tower') {
      if (prm.t_start === prm.t_end) errors.push('t_end: equals t_start');
      else {
        const levels = Math.floor(Math.abs(prm.t_start - prm.t_end) / prm.t_step) + 1;
        if (levels < 2 || levels > 16) errors.push('t_step: 2..16 levels');
      }
    } else if (testId === 'flow') {
      if (prm.f_start + 8 * prm.f_step > 160) errors.push('f_step: the last plate above 160 %');
    } else if (testId === 'pressure_advance') {
      if (prm.pa_end <= prm.pa_start) errors.push('pa_end: not above pa_start');
      else {
        const n = pyRound((prm.pa_end - prm.pa_start) / prm.pa_step) + 1;
        if (n < 3 || n > 31) errors.push('pa_step: 3..31 lines');
      }
    } else if (testId === 'retraction') {
      if (prm.r_start + (prm.r_count - 1) * prm.r_step > 15) errors.push('r_step: the last level above 15 mm');
    } else if (testId === 'max_flow') {
      if (prm.v_end < prm.v_start + 4) errors.push('v_end: at least 4 mm³/s above v_start');
    } else if (testId === 'ringing') {
      if (prm.a_start > printer.max_accel) errors.push("a_start: above the printer's max acceleration");
    }
    return errors;
  }

  function numbers(text) {
    const out = [];
    const re = /[-+]?\d+(?:[.,]\d+)?/g;
    let m;
    while ((m = re.exec(text || ''))) out.push(parseFloat(m[0].replace(',', '.')));
    return out;
  }

  function helper(testId, text, printer, material, prm) {
    const info = testInfo(testId);
    if (!info.helper) return { ok: false, error: 'no_helper' };
    const nums = numbers(text);
    const raw = (text || '').trim();
    if (!nums.length) return { ok: false, error: 'need_number' };
    const v = nums[0];
    const dotted = raw.indexOf('.') >= 0 || raw.indexOf(',') >= 0;
    switch (info.helper.kind) {
      case 'temp': return { ok: true, value: String(Math.trunc(pyRound(v))), unit: '°C', note: 'helper_temp' };
      case 'flow': return { ok: true, value: fixed(material.flow * v / 100, 3), unit: '', note: 'helper_flow' };
      case 'pa': return { ok: true, value: fixed(dotted ? v : v / 1000, 3), unit: '', note: 'helper_pa' };
      case 'retraction': return { ok: true, value: trim(dotted ? v : v / 10, 2), unit: 'mm', note: 'helper_retraction' };
      case 'max_flow': return { ok: true, value: fixed(v * 0.85, 1), unit: 'mm³/s', note: 'helper_max_flow' };
      case 'overhang': return { ok: true, value: String(Math.trunc(pyRound(90 - v))), unit: '°', note: 'helper_overhang' };
      case 'ringing': {
        const n = Math.trunc(pyRound(v));
        let accels = [];
        for (let i = 0; i < prm.a_count; i++) accels.push(prm.a_start + prm.a_step * i);
        accels = accels.filter((a) => a <= printer.max_accel);
        if (n < 1 || n > accels.length) return { ok: false, error: 'out_of_range' };
        if (n === 1) return { ok: true, value: String(Math.floor(accels[0] / 2)), unit: 'mm/s²', note: 'helper_ringing_first' };
        return { ok: true, value: String(accels[n - 2]), unit: 'mm/s²', note: 'helper_ringing' };
      }
      case 'tolerance': return { ok: true, value: fixed(dotted ? v : v / 100, 2), unit: 'mm', note: 'helper_tolerance' };
      case 'cube': {
        if (nums.length < 3) return { ok: false, error: 'need_three' };
        const size = prm.size === undefined ? 20 : prm.size;
        const [dx, dy, dz] = nums.slice(0, 3).map((n) => n - size);
        if (Math.max(Math.abs(dx), Math.abs(dy), Math.abs(dz)) <= 0.1) return { ok: true, value: 'OK', unit: '', note: 'helper_cube_ok' };
        if (Math.max(dx, dy) - Math.min(dx, dy) <= 0.1 && dx * dy > 0) {
          const avg = (nums[0] + nums[1]) / 2;
          return { ok: true, value: fixed(material.flow * size / avg, 3), unit: '', note: 'helper_cube_flow' };
        }
        return { ok: true, value: Math.abs(dx) > Math.abs(dy) ? 'X' : 'Y', unit: '', note: 'helper_cube_axis' };
      }
      default: return { ok: false, error: 'no_helper' };
    }
  }

  function summary(res) {
    return { name: res.name, minutes: pyRound(res.time / 60), grams: fixed(res.grams, 1),
      lines: res.g.lines.length, max_z: fixed(res.max_z, 2) };
  }

  const api = { tests, testInfo, normalize, validate, helper, summary };
  C3D.params = api;
  if (isNode) module.exports = api;
})();
