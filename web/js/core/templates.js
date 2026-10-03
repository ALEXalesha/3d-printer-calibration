// Start and end code templates - twin of python/calib3d/core/templates.py.
(function () {
  'use strict';
  const root = typeof globalThis !== 'undefined' ? globalThis : window;
  const C3D = root.C3D || (root.C3D = {});
  const isNode = typeof module === 'object' && module.exports;

  const NAME = /\{([a-z_][a-z0-9_]*)\}/g;
  const FLAG = /^\{\?(!?)([a-z_][a-z0-9_]*)\}/;

  /** -> [lines, unknown names in order of appearance] */
  function expand(lines, values, flags) {
    const out = [];
    const unknown = [];
    for (let line of lines) {
      const m = FLAG.exec(line);
      if (m) {
        let on = !!flags[m[2]];
        if (m[1] === '!') on = !on;
        if (!on) continue;
        line = line.slice(m[0].length);
      }
      const done = line.replace(NAME, (all, key) => {
        if (Object.prototype.hasOwnProperty.call(values, key)) return values[key];
        if (unknown.indexOf(key) < 0) unknown.push(key);
        return all;
      });
      for (const part of done.split('\n')) out.push(part);
    }
    return [out, unknown];
  }

  function placeholders(lines) {
    const names = [];
    const flags = [];
    for (let line of lines) {
      const m = FLAG.exec(line);
      if (m) {
        if (flags.indexOf(m[2]) < 0) flags.push(m[2]);
        line = line.slice(m[0].length);
      }
      let mm;
      const re = new RegExp(NAME.source, 'g');
      while ((mm = re.exec(line))) if (names.indexOf(mm[1]) < 0) names.push(mm[1]);
    }
    return [names, flags];
  }

  const api = { expand, placeholders };
  C3D.templates = api;
  if (isNode) module.exports = api;
})();
