// Preview data (top and front views) - twin of python/calib3d/core/preview.py.
(function () {
  'use strict';
  const root = typeof globalThis !== 'undefined' ? globalThis : window;
  const C3D = root.C3D || (root.C3D = {});
  const isNode = typeof module === 'object' && module.exports;

  const COLORS = { top: '#fafafa', wall: '#eb7828', inner: '#c8aa3c', infill: '#787878', slab: '#5a8cdc',
    bridge: '#285aff', base: '#969696', label: '#ff2828', slow: '#3cb45a', fast: '#e63ca0' };

  function previewData(res) {
    const g = res.g, ctx = g.ctx;
    const ox = ctx.ox, oy = ctx.oy;
    const segs = g.segments.map((s) => [s[0] + ox, s[1] + oy, s[2] + ox, s[3] + oy, s[4], s[5]]);
    const bed = ctx.p.bed;
    const out = { bed: { x: bed.x, y: bed.y, origin: bed.origin, shape: bed.shape }, top: [], front: null, max_z: res.max_z };
    if (!segs.length) return out;
    let zmin = Infinity, zmax = -Infinity;
    for (const s of segs) { zmin = Math.min(zmin, s[4]); zmax = Math.max(zmax, s[4]); }
    const topCut = zmin + ctx.H * 1.05;
    out.top = segs.filter((s) => s[4] <= topCut || s[5] === 'label').map((s) => [s[0], s[1], s[2], s[3], s[5]]);
    if (zmax > 2 && segs.some((s) => s[4] > 1.0)) {
      let yFront = Infinity;
      for (const s of segs) if (s[5] !== 'label' && s[4] > 1.0) yFront = Math.min(yFront, Math.min(s[1], s[3]));
      const front = segs.filter((s) => Math.min(s[1], s[3]) < yFront + 1.5 || s[5] === 'label')
        .map((s) => [s[0], s[4], s[2], s[4], s[5]]);
      // stable sort: labels last (Python sorts on the key False/True the same way)
      const plain = front.filter((s) => s[4] !== 'label');
      const labels = front.filter((s) => s[4] === 'label');
      out.front = plain.concat(labels);
    }
    return out;
  }

  /** All segments in printer coordinates, for the 3D view: [x1, y1, x2, y2, z, kind]. */
  function layers(res) {
    const g = res.g, ox = g.ctx.ox, oy = g.ctx.oy;
    return g.segments.map((s) => [s[0] + ox, s[1] + oy, s[2] + ox, s[3] + oy, s[4], s[5]]);
  }

  const api = { previewData, layers, COLORS };
  C3D.preview = api;
  if (isNode) module.exports = api;
})();
