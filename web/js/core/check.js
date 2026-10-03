// G-code check (mini-simulation of the finished file) - twin of python/calib3d/core/check.py.
// Both return the same list of problems for the same text.
(function () {
  'use strict';
  const root = typeof globalThis !== 'undefined' ? globalThis : window;
  const C3D = root.C3D || (root.C3D = {});
  const isNode = typeof module === 'object' && module.exports;
  if (isNode) { require('./data.js'); require('./num.js'); require('./generator.js'); }
  const { fixed, hypot, pyRound, trim } = C3D.num;

  const NO_MIN_TIME = ['max_flow', 'ringing', 'first_layer', 'pressure_advance'];
  const MIN_TIME_SHARE = 0.7;
  const BRACES = /\{[^{}\n]*\}/;

  function parse(line) {
    const code = line.split(';', 1)[0].trim();
    if (!code) return [null, {}];
    const sp = code.search(/\s/);
    const head = (sp < 0 ? code : code.slice(0, sp)).toUpperCase();
    const rest = sp < 0 ? '' : code.slice(sp).trim();
    const w = {};
    if (/^(SET_|M|G|T)/.test(head) && rest.indexOf('=') >= 0) {
      const re = /([A-Za-z_]+)=(\S+)/g;
      let m;
      while ((m = re.exec(rest))) w[m[1].toUpperCase()] = m[2];
      return [head, w];
    }
    const re = /([A-Z])([-+]?\d*\.?\d+)/g;
    let m;
    const up = rest.toUpperCase();
    while ((m = re.exec(up))) w[m[1]] = parseFloat(m[2]);
    return [head, w];
  }

  function foreignWords(printer) {
    const fws = C3D.data.firmware;
    const own = printer.firmware;
    const cmds = C3D.generator.firmwareCommands(printer);
    const allowed = new Set();
    for (const v of Object.values(cmds)) {
      for (const s of (Array.isArray(v) ? v : v ? [v] : [])) allowed.add(s.split(/\s+/)[0].toUpperCase());
    }
    const foreign = new Set();
    for (const [fid, fw] of Object.entries(fws)) {
      if (fid.startsWith('_') || fid === own) continue;
      for (const w of fw.signature) if (!allowed.has(w.toUpperCase())) foreign.add(w.toUpperCase());
    }
    return foreign;
  }

  function inside(printer, x, y, margin) {
    const bed = printer.bed;
    if (bed.shape === 'round') return hypot(x, y) <= Math.min(bed.x, bed.y) / 2 - margin;
    if (bed.origin === 'center') return Math.abs(x) <= bed.x / 2 - margin && Math.abs(y) <= bed.y / 2 - margin;
    return margin <= x && x <= bed.x - margin && margin <= y && y <= bed.y - margin;
  }

  function check(text, printer, material, testId, bodyStart, bodyEnd, maxZ, stats) {
    const problems = [];
    const bad = (code, msg) => {
      if (problems.filter((p) => p.startsWith(code + ':')).length < 5) problems.push(`${code}: ${msg}`);
    };
    let lines = text.split('\n');
    if (text.endsWith('\n')) lines = lines.slice(0, -1);
    const b0 = bodyStart === undefined || bodyStart === null ? 0 : bodyStart;
    const b1 = bodyEnd === undefined || bodyEnd === null ? lines.length : bodyEnd;

    for (let i = 0; i < lines.length; i++) {
      const m = BRACES.exec(lines[i]);
      if (m) bad('placeholder', `line ${i + 1}: ${m[0]}`);
    }

    const foreign = foreignWords(printer);
    const nozzle = printer.nozzle;
    const filArea = Math.PI * (printer.filament_diameter / 2) * (printer.filament_diameter / 2);
    const maxFPrint = printer.max_speed * 60 + 0.5;
    const maxFAny = Math.max(printer.max_speed, printer.travel_speed) * 60 + 0.5;
    const t = material.tower;
    const tLo = Math.min(t.start, t.end, material.nozzle_temp, material.first_layer_temp) - 15;
    const tHi = Math.max(t.start, t.end, material.nozzle_temp, material.first_layer_temp) + 15;
    const zTop = printer.bed.z;
    const zLimit = maxZ !== undefined && maxZ !== null ? maxZ + printer.retract.z_hop + 0.001 : zTop;
    const h = pyRound(0.5 * nozzle, 3);
    const areaLo = 0.2 * nozzle * h, areaHi = 2.5 * nozzle * h;
    const useMinTime = NO_MIN_TIME.indexOf(testId) < 0;
    const minTime = material.min_layer_time;

    let x = 0, y = 0, z = 0, f = 0;
    let absolute = true;
    let layerTime = null, layerFloor = true, layerNo = -1, lastLayerZ = -1.0, retracted = 0.0;
    const has = (w, k) => Object.prototype.hasOwnProperty.call(w, k);

    const closeLayer = () => {
      if (layerTime === null || !useMinTime || layerNo < 1) return;
      if (stats && !layerFloor) stats.push(layerTime / minTime);
      if (layerTime < minTime * MIN_TIME_SHARE && !layerFloor) {
        bad('min_layer_time', `layer ${layerNo}: ${fixed(layerTime, 1)} s < ${fixed(minTime, 1)} s`);
      }
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const [head, w] = parse(line);
      const inBody = b0 <= i && i < b1;
      if (line.startsWith(';LAYER_CHANGE') && inBody) {
        closeLayer();
        layerNo += 1;
        layerTime = 0.0;
        layerFloor = true;
      }
      if (inBody && line.startsWith(';Z:')) {
        const lz = parseFloat(line.slice(3));
        if (lz <= lastLayerZ) bad('layers', `line ${i + 1}: layer Z ${trim(lz, 3)} not above ${trim(lastLayerZ, 3)}`);
        lastLayerZ = lz;
      }
      if (head === null) continue;
      if (foreign.has(head)) bad('foreign_command', `line ${i + 1}: ${head}`);
      if (head === 'G90') absolute = true;
      else if (head === 'G91') absolute = false;
      else if ((head === 'M104' || head === 'M109') && has(w, 'S') && w.S > 0 && inBody) {
        if (!(tLo <= w.S && w.S <= tHi)) bad('temperature', `line ${i + 1}: nozzle ${trim(w.S, 1)} outside ${tLo}..${tHi}`);
      } else if ((head === 'M140' || head === 'M190') && has(w, 'S') && w.S > 0) {
        if (w.S > 130 || Math.abs(w.S - material.bed) > 0.5) bad('temperature', `line ${i + 1}: bed ${trim(w.S, 1)}, material ${material.bed}`);
      } else if (head === 'SET_VELOCITY_LIMIT' && has(w, 'ACCEL')) {
        if (parseFloat(w.ACCEL) > printer.max_accel) bad('accel', `line ${i + 1}: ${w.ACCEL} > ${printer.max_accel}`);
      } else if (head === 'M204') {
        for (const k of ['S', 'P', 'T']) {
          if (has(w, k) && w[k] > printer.max_accel) bad('accel', `line ${i + 1}: ${trim(w[k], 1)} > ${printer.max_accel}`);
        }
      } else if (head === 'G0' || head === 'G1') {
        if (has(w, 'F')) f = w.F;
        const nx = absolute ? (has(w, 'X') ? w.X : x) : x + (has(w, 'X') ? w.X : 0.0);
        const ny = absolute ? (has(w, 'Y') ? w.Y : y) : y + (has(w, 'Y') ? w.Y : 0.0);
        const nz = absolute ? (has(w, 'Z') ? w.Z : z) : z + (has(w, 'Z') ? w.Z : 0.0);
        const e = has(w, 'E') ? w.E : 0.0;
        const d = hypot(nx - x, ny - y);
        if (inBody) {
          if (has(w, 'Z') && (nz > zLimit + 1e-9 || nz > zTop)) bad('z_max', `line ${i + 1}: Z${trim(nz, 3)}`);
          if (d > 0) {
            if (!inside(printer, nx, ny, e <= 0 ? 0.0 : 1.0)) bad('outside_bed', `line ${i + 1}: X${trim(nx, 3)} Y${trim(ny, 3)}`);
            if (f < 300 - 1e-9) bad('speed', `line ${i + 1}: F${trim(f, 1)} < 300`);
            if (f > (e > 0 ? maxFPrint : maxFAny)) bad('speed', `line ${i + 1}: F${trim(f, 1)} above the printer limit`);
            if (e < 0) bad('extrusion', `line ${i + 1}: negative E on a move`);
            else if (e > 0) {
              const a = e * filArea / d;
              if (!(areaLo <= a && a <= areaHi)) bad('extrusion', `line ${i + 1}: cross-section ${fixed(a, 4)} mm2 not plausible for nozzle ${trim(nozzle, 2)}`);
            }
            if (layerTime !== null && f > 0) {
              layerTime += d / (f / 60);
              if (e > 0 && f > 600.5) layerFloor = false;
            }
          } else if (has(w, 'Z') && layerTime !== null && f > 0) {
            layerTime += Math.abs(nz - z) / (f / 60);
          }
          if (d === 0 && e !== 0 && !has(w, 'X') && !has(w, 'Y') && !has(w, 'Z')) {
            if (layerTime !== null && f > 0) layerTime += Math.abs(e) / (f / 60);
            if (e < 0) {
              if (retracted > 0) bad('retraction', `line ${i + 1}: retract twice`);
              retracted = -e;
            } else {
              if (retracted === 0) bad('retraction', `line ${i + 1}: push back without a retract`);
              else if (Math.abs(e - retracted) > 0.0051) bad('retraction', `line ${i + 1}: back ${trim(e, 3)} after retract ${trim(retracted, 3)}`);
              retracted = 0.0;
            }
          }
        }
        x = nx; y = ny; z = nz;
      }
    }
    closeLayer();
    return problems;
  }

  function checkResult(res, testId) {
    const g = res.g;
    return check(res.text, g.ctx.p, g.ctx.m, testId, g.body_start, g.body_end, res.max_z);
  }

  const api = { check, checkResult, parse, NO_MIN_TIME };
  C3D.check = api;
  if (isNode) module.exports = api;
})();
