// Where the head ends up after the start code - twin of python/calib3d/core/gcode_sim.py.
(function () {
  'use strict';
  const root = typeof globalThis !== 'undefined' ? globalThis : window;
  const C3D = root.C3D || (root.C3D = {});
  const isNode = typeof module === 'object' && module.exports;

  function words(line) {
    const code = line.split(';', 1)[0].trim().toUpperCase();
    if (!code) return [null, {}];
    const sp = code.search(/\s/);
    const head = sp < 0 ? code : code.slice(0, sp);
    const rest = sp < 0 ? '' : code.slice(sp).trim();
    const w = {};
    const re = /([A-Z])([-+]?\d*\.?\d+)/g;
    let m;
    while ((m = re.exec(rest))) w[m[1]] = parseFloat(m[2]);
    return [head, w];
  }

  function endState(lines, heatTime) {
    if (heatTime === undefined) heatTime = 240.0;
    let x = 0, y = 0, z = 0, eTotal = 0;
    let absolute = true, eAbsolute = false, ePos = 0, eModeSet = false;
    const has = (w, k) => Object.prototype.hasOwnProperty.call(w, k);
    for (const line of lines) {
      const [head, w] = words(line);
      if (head === null) continue;
      if (head === 'G90') absolute = true;
      else if (head === 'G91') absolute = false;
      else if (head === 'M82') { eAbsolute = true; eModeSet = true; }
      else if (head === 'M83') { eAbsolute = false; eModeSet = true; }
      else if (head === 'G92') {
        if (has(w, 'E')) ePos = w.E;
        if (has(w, 'X')) x = w.X;
        if (has(w, 'Y')) y = w.Y;
        if (has(w, 'Z')) z = w.Z;
      } else if (head === 'G28') {
        const none = Object.keys(w).length === 0;
        if (none || has(w, 'X')) x = 0;
        if (none || has(w, 'Y')) y = 0;
        if (none || has(w, 'Z')) z = 0;
      } else if (head === 'G0' || head === 'G1' || head === 'G2' || head === 'G3') {
        if (absolute) {
          if (has(w, 'X')) x = w.X;
          if (has(w, 'Y')) y = w.Y;
          if (has(w, 'Z')) z = w.Z;
        } else {
          x = x + (has(w, 'X') ? w.X : 0);
          y = y + (has(w, 'Y') ? w.Y : 0);
          z = z + (has(w, 'Z') ? w.Z : 0);
        }
        if (has(w, 'E')) {
          let de;
          if (eAbsolute) { de = w.E - ePos; ePos = w.E; } else de = w.E;
          if (de > 0) eTotal += de;
        }
      }
    }
    return { x, y, z, e: eTotal, time: heatTime, absolute, e_relative_set: eModeSet && !eAbsolute };
  }

  const api = { words, endState };
  C3D.gcodeSim = api;
  if (isNode) module.exports = api;
})();
