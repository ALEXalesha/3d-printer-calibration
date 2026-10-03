// Numbers that must come out the same as in Python (python/calib3d/core/num.py).
// hypot: CPython's math.hypot written out with exact products; fixed: Python's
// f"{x:.Nf}" (toFixed rounds exact halves up, Python to even); pyRound: Python round().
(function () {
  'use strict';
  const root = typeof globalThis !== 'undefined' ? globalThis : window;
  const C3D = root.C3D || (root.C3D = {});
  const isNode = typeof module === 'object' && module.exports;
  if (isNode) require('./data.js');

  const SPLIT = 134217729.0; // 2**27 + 1
  const DBL_MIN = 2.2250738585072014e-308;

  function twoProd(a, b) {
    const p = a * b;
    let t = SPLIT * a;
    const ah = t - (t - a);
    const al = a - ah;
    t = SPLIT * b;
    const bh = t - (t - b);
    const bl = b - bh;
    return [p, ((ah * bh - p) + ah * bl + al * bh) + al * bl];
  }

  // frexp exponent: m * 2^e with 0.5 <= m < 1 (finite, positive input)
  function frexpExp(x) {
    if (x === 0) return 0;
    let e = Math.max(-1023, Math.floor(Math.log2(x)) + 1);
    let m = x * Math.pow(2, -e);
    while (m < 0.5) { m *= 2; e -= 1; }
    while (m >= 1) { m /= 2; e += 1; }
    return e;
  }

  function hypot(x, y) {
    x = Math.abs(x); y = Math.abs(y);
    const mx = x > y ? x : y;
    if (mx === 0) return 0;
    const e = frexpExp(mx);
    if (e < -1023) return DBL_MIN * hypot(x / DBL_MIN, y / DBL_MIN);
    const scale = Math.pow(2, -e);
    let csum = 1.0, frac1 = 0.0, frac2 = 0.0;
    for (let v of [x, y]) {
      v *= scale;
      const [hi, lo] = twoProd(v, v);
      const s = csum + hi;
      frac2 += (csum - s) + hi;
      csum = s;
      frac1 += lo;
    }
    let h = Math.sqrt(csum - 1.0 + (frac1 + frac2));
    const [hi, lo] = twoProd(-h, h);
    const s = csum + hi;
    frac2 += (csum - s) + hi;
    csum = s;
    frac1 += lo;
    h += (csum - 1.0 + (frac1 + frac2)) / (2.0 * h);
    return h / scale;
  }

  function sq(x) { return x * x; }

  // one unit less in the last digit of a non-negative decimal string
  function decLast(s) {
    const ch = s.split('');
    for (let i = ch.length - 1; i >= 0; i--) {
      if (ch[i] === '.') continue;
      if (ch[i] !== '0') { ch[i] = String.fromCharCode(ch[i].charCodeAt(0) - 1); break; }
      ch[i] = '9';
    }
    let out = ch.join('');
    // "09.5" -> "9.5"
    while (out.length > 1 && out[0] === '0' && out[1] !== '.') out = out.slice(1);
    return out;
  }

  /** f"{x:.{d}f}" of Python. */
  function fixed(x, d) {
    if (!Number.isFinite(x)) return x > 0 ? 'inf' : x < 0 ? '-inf' : 'nan';
    const neg = x < 0 || Object.is(x, -0);
    const a = Math.abs(x);
    let s = a.toFixed(d);
    // An exact half at d digits means a * 2^(d+1) is an odd integer; toFixed went up,
    // Python goes to the even neighbour.
    const t = a * Math.pow(2, d + 1);
    if (Number.isInteger(t) && t < 9007199254740992 && t % 2 === 1) {
      const last = s.charCodeAt(s.length - 1) - 48;
      if (last % 2 === 1) s = decLast(s);
    }
    return (neg ? '-' : '') + s;
  }

  /** Python round(x) / round(x, d). */
  function pyRound(x, d) {
    if (d === undefined) {
      const f = Math.floor(x) + 0;     // + 0: Python's round(-0.0) is the integer 0, not -0
      const diff = x - f;
      if (diff < 0.5) return f;
      if (diff > 0.5) return f + 1;
      return f % 2 === 0 ? f : f + 1;
    }
    return parseFloat(fixed(x, d));
  }

  /** str(x) of a Python float. */
  function pyRepr(x) {
    const a = Math.abs(x);
    if (Object.is(x, -0)) return '-0.0';
    if (Number.isInteger(x) && a < 1e16) return x.toFixed(1);
    if (a !== 0 && (a < 1e-4 || a >= 1e16)) {
      const [m, e] = x.toExponential().split('e');
      const n = parseInt(e, 10);
      return m + 'e' + (n < 0 ? '-' : '+') + String(Math.abs(n)).padStart(2, '0');
    }
    return String(x);
  }

  function trim(x, d) {
    let s = fixed(x, d);
    if (s.indexOf('.') >= 0) s = s.replace(/0+$/, '').replace(/\.$/, '');
    return (s === '-0' || s === '') ? '0' : s;
  }

  function parseHexDouble(h) {
    // "0x1.74b49cf3902d4p-2" (float.hex of Python)
    const m = /^(-?)0x([01])\.([0-9a-f]*)p([-+]\d+)$/i.exec(h);
    if (!m) throw new Error('bad hex double ' + h);
    let mant = parseInt(m[2], 16);
    const frac = m[3];
    for (let i = 0; i < frac.length; i++) mant += parseInt(frac[i], 16) / Math.pow(16, i + 1);
    const v = mant * Math.pow(2, parseInt(m[4], 10));
    return m[1] ? -v : v;
  }

  let TAN = null;
  function tanDeg(a) {
    a = Math.trunc(a);
    if (a < 0 || a > 89) throw new Error('angle ' + a + ' out of 0..89');
    if (!TAN) TAN = C3D.data.tables.tan_deg.map(parseHexDouble);
    return TAN[a];
  }

  const api = { hypot, sq, fixed, pyRound, pyRepr, trim, tanDeg, parseHexDouble, frexpExp };
  C3D.num = api;
  if (isNode) module.exports = api;
})();
