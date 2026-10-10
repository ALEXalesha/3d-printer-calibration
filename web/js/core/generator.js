// The G-code generator - a line-by-line translation of python/calib3d/core/generator.py
// (which itself follows reference/calibration.py). Both must give the same bytes; the
// equality law (tests/py/test_equality.py) checks it on a matrix of profiles. Every number
// on its way into the file goes through num.js (fixed, pyRound, hypot).
(function () {
  'use strict';
  const root = typeof globalThis !== 'undefined' ? globalThis : window;
  const C3D = root.C3D || (root.C3D = {});
  const isNode = typeof module === 'object' && module.exports;
  if (isNode) {
    require('./data.js'); require('./num.js'); require('./templates.js'); require('./profiles.js');
    require('./gcode_sim.js');
  }
  const { fixed, hypot, pyRound, pyRepr, sq, trim, tanDeg } = C3D.num;
  const P = C3D.profiles;

  function text(key, lang, values) {
    let s = C3D.data.gcode_text[key][lang === 'en' ? 'en' : 'ru'];
    for (const k of Object.keys(values || {})) s = s.split('{' + k + '}').join(values[k]);
    return s;
  }

  class TemplateError extends Error {
    constructor(names) {
      super('unknown placeholders: ' + names.map((n) => '{' + n + '}').join(', '));
      this.names = names;
      this.kind = 'template';
    }
  }

  // Parameters that params.validate() rejects: they never reach G-code.
  class ParamError extends Error {
    constructor(errors) { super('parameters: ' + errors.join('; ')); this.kind = 'params'; this.errors = errors; }
  }
  class DoesNotFit extends Error {
    constructor(msg) { super(msg); this.kind = 'does_not_fit'; }
  }

  function firmwareCommands(printer) {
    const fw = C3D.data.firmware[printer.firmware];
    const out = {};
    for (const k of ['pressure_advance', 'accel', 'accel_band', 'layer_progress', 'fan']) out[k] = fw[k];
    const ov = printer.fw_overrides || {};
    for (const k of Object.keys(ov)) if (k in out) out[k] = ov[k];
    return out;
  }

  function area(w, h) {
    return (w - h) * h + Math.PI * sq(h / 2);
  }

  class Ctx {
    constructor(printer, material, lang, shift) {
      shift = shift || [0.0, 0.0];
      this.p = printer;
      this.m = material;
      this.lang = lang || 'ru';
      this.fw = firmwareCommands(printer);
      const n = printer.nozzle;
      this.NOZ = n;
      this.W = pyRound(1.125 * n, 3);
      this.W1 = pyRound(1.25 * n, 3);
      this.H = pyRound(0.5 * n, 3);
      this.LW = n;
      this.WW = pyRound(1.5 * n, 3);
      this.HH = pyRound(0.75 * n, 3);
      this.FIL_AREA = Math.PI * sq(printer.filament_diameter / 2);
      const r = printer.retract;
      this.RETRACT = r.length;
      this.RETRACT_F = r.speed * 60;
      this.ZHOP = r.z_hop;
      this.TRAVEL_F = printer.travel_speed * 60;
      this.Z_F = printer.z_speed * 60;
      this.MAX_SPEED = printer.max_speed;
      const bed = printer.bed;
      if (bed.origin === 'center') {
        this.ox = -128.0 + shift[0];
        this.oy = -128.0 + shift[1];
      } else {
        this.ox = bed.x / 2 - 128 + shift[0];
        this.oy = bed.y / 2 - 128 + shift[1];
      }
    }
    px(x) { return x + this.ox; }
    py(y) { return y + this.oy; }
  }

  class Gcode {
    constructor(ctx) {
      this.ctx = ctx;
      this.mat = ctx.m;
      this.lines = [];
      this.x = 0.0; this.y = 0.0; this.z = 0.0;
      this.retracted = false;
      this.segments = [];
      this.time = 0.0;
      this.e_total = 0.0;
      this.retract_len = ctx.RETRACT;
      this.body_start = 0;
      this.body_end = null;
      this.fixed_temp = false;
    }

    out(s) { this.lines.push(s); }

    retract() {
      if (!this.retracted && this.retract_len > 0) {
        const c = this.ctx;
        this.out(`G1 E-${fixed(this.retract_len, 2)} F${fixed(c.RETRACT_F, 0)}`);
        this.time += this.retract_len / (c.RETRACT_F / 60);
        this.retracted = this.retract_len;
      }
    }

    unretract() {
      if (this.retracted) {
        const c = this.ctx;
        this.out(`G1 E${fixed(this.retracted, 2)} F${fixed(c.RETRACT_F, 0)}`);
        this.time += this.retracted / (c.RETRACT_F / 60);
        this.retracted = false;
      }
    }

    travel(x, y, hop) {
      if (hop === undefined) hop = true;
      const c = this.ctx;
      const d = hypot(x - this.x, y - this.y);
      if (d < 0.01) return;
      const longMove = d > 2.0;
      if (longMove) {
        this.retract();
        if (hop && c.ZHOP > 0) this.out(`G1 Z${fixed(this.z + c.ZHOP, 3)} F${fixed(c.Z_F, 0)}`);
      }
      this.out(`G1 X${fixed(c.px(x), 3)} Y${fixed(c.py(y), 3)} F${fixed(c.TRAVEL_F, 0)}`);
      if (longMove && hop && c.ZHOP > 0) this.out(`G1 Z${fixed(this.z, 3)} F${fixed(c.Z_F, 0)}`);
      this.time += d / (c.TRAVEL_F / 60) + (longMove ? 0.1 : 0);
      this.x = x; this.y = y;
    }

    extrude(x, y, w, h, speed, kind, flow, cap) {
      if (cap === undefined) cap = true;
      const c = this.ctx;
      const d = hypot(x - this.x, y - this.y);
      if (d < 0.01) return;
      this.unretract();
      const e = d * area(w, h) / c.FIL_AREA * (flow !== undefined && flow !== null ? flow : this.mat.flow);
      if (cap) speed = Math.min(speed, this.mat.mvs * 0.9 / area(w, h));
      if (speed > c.MAX_SPEED) speed = c.MAX_SPEED;
      this.out(`G1 X${fixed(c.px(x), 3)} Y${fixed(c.py(y), 3)} E${fixed(e, 5)} F${fixed(speed * 60, 0)}`);
      this.segments.push([this.x, this.y, x, y, this.z, kind]);
      this.time += d / speed;
      this.e_total += e;
      this.x = x; this.y = y;
    }

    path(pts, w, h, speed, kind, closed, flow) {
      if (!pts.length) return;
      this.travel(pts[0][0], pts[0][1]);
      for (let i = 1; i < pts.length; i++) this.extrude(pts[i][0], pts[i][1], w, h, speed, kind, flow);
      if (closed) this.extrude(pts[0][0], pts[0][1], w, h, speed, kind, flow);
    }

    fan(frac) {
      this.out(this.ctx.fw.fan.split('{s255}').join(String(pyRound(255 * frac))).split('{s1}').join(fixed(frac, 2)));
    }

    layer(n, z, h, total) {
      const c = this.ctx;
      this.out(';LAYER_CHANGE');
      this.out(`;Z:${fixed(z, 2)}`);
      this.out(`;HEIGHT:${fixed(h, 2)}`);
      this.out(`;LAYER:${n}`);
      this.retract();
      this.out(`G1 Z${fixed(z, 3)} F${fixed(c.Z_F, 0)}`);
      if (c.fw.layer_progress) this.out(c.fw.layer_progress.split('{total}').join(String(total)).split('{n}').join(String(n + 1)));
      this.z = z;
      if (n === 1 && this.mat.nozzle_temp !== this.mat.first_layer_temp && !this.fixed_temp) {
        this.out(`M104 S${this.mat.nozzle_temp}` + text('first_layer_temp_switch', c.lang));
      }
    }

    accel(a, band) {
      for (const s of this.ctx.fw[band ? 'accel_band' : 'accel']) this.out(s.split('{a}').join(String(a)));
    }

    pressureAdvance(v, comment) {
      this.out(this.ctx.fw.pressure_advance.split('{v}').join(fixed(v, 3)) + (comment || ''));
    }
  }

  // ---------- start and end ----------

  function purgeGeometry(ctx) {
    const bed = ctx.p.bed;
    let a, b, c, d;
    if (bed.shape === 'round') {
      const r = Math.min(bed.x, bed.y) / 2;
      const y0 = -(r - 8);
      const half = Math.min(50.0, Math.sqrt(r * r - y0 * y0) - 5);
      a = [-half, y0]; b = [half, y0];
      c = [half, y0 + 1.0]; d = [-half, y0 + 1.0];
    } else {
      const x0 = bed.origin === 'center' ? -bed.x / 2 : 0.0;
      const y0 = bed.origin === 'center' ? -bed.y / 2 : 0.0;
      const length = Math.min(100.0, bed.y - 40);
      a = [x0 + 3, y0 + 20]; b = [x0 + 3, y0 + 20 + length];
      c = [x0 + 4, y0 + 20 + length]; d = [x0 + 4, y0 + 20];
    }
    const length = hypot(b[0] - a[0], b[1] - a[1]);
    const e = length * area(2 * ctx.NOZ, 0.3) / ctx.FIL_AREA;
    return [a, b, c, d, e];
  }

  // Where the end code parks the head: a corner of a rectangular bed, the front of a round one
  // (its corner lies outside the circle).
  function parkPoint(bed) {
    if (bed.shape === 'round') return [0.0, -(Math.min(bed.x, bed.y) / 2 - 10)];
    if (bed.origin === 'center') return [-bed.x / 2 + 5, bed.y / 2 - 5];
    return [5.0, bed.y - 5];
  }

  function templateValues(ctx, firstTemp, title, totalLayers, maxZ) {
    const p = ctx.p, m = ctx.m;
    const park = parkPoint(p.bed);
    const mvs = m.mvs;
    const f1 = Math.min(6000, Math.max(900, mvs / 0.5 / 0.3 * 60));
    const f2 = Math.min(12000, Math.max(1200, mvs / 0.5 / 0.3 * 60));
    const bedZ = p.bed.z;
    let capped;
    if (maxZ > 100) capped = fixed(Math.min(maxZ + 50, bedZ + 0.5), 2);
    else if (bedZ < 100) capped = fixed(Math.min(maxZ + 10, bedZ), 2);
    else capped = '100';
    const [a, b, c, d, e] = purgeGeometry(ctx);
    const v = {
      nozzle_temp: String(m.nozzle_temp),
      first_layer_nozzle_temp: String(firstTemp),
      bed_temp: String(m.bed),
      max_z: fixed(maxZ, 2),
      max_z_plus_half: fixed(maxZ + 0.5, 2),
      max_z_plus_50_capped: capped,
      park_z: fixed(Math.min(maxZ + 10, bedZ), 2),
      filament_type: m.type,
      layer_height: fixed(ctx.H, 2),
      print_title: title,
      total_layers: String(totalLayers),
      accel: String(p.default_accel),
      set_accel: ctx.fw.accel.map((s) => s.split('{a}').join(String(p.default_accel))).join('\n'),
      purge_f1: fixed(f1, 0),
      purge_f2: fixed(f2, 0),
      purge_f2_slow: fixed(0.2 * f2, 0),
      travel_f: fixed(ctx.TRAVEL_F, 0),
      z_f: fixed(ctx.Z_F, 0),
      retract_len: fixed(ctx.RETRACT, 2),
      retract_f: fixed(ctx.RETRACT_F, 0),
      bed_x: trim(p.bed.x, 2),
      bed_y: trim(p.bed.y, 2),
      purge_x0: fixed(a[0], 2), purge_y0: fixed(a[1], 2),
      purge_x1: fixed(b[0], 2), purge_y1: fixed(b[1], 2),
      purge_x2: fixed(c[0], 2), purge_y2: fixed(c[1], 2),
      purge_x3: fixed(d[0], 2), purge_y3: fixed(d[1], 2),
      purge_e: fixed(e, 3),
      park_x: fixed(park[0], 2),
      park_y: fixed(park[1], 2),
    };
    const flags = Object.assign({}, p.options || {});
    flags.pla_hot_bed = m.type === 'PLA' && m.bed > 50;
    return [v, flags];
  }

  function expandTemplate(ctx, lines, values, flags) {
    const [out, unknown] = C3D.templates.expand(lines, values, flags);
    if (unknown.length) throw new TemplateError(unknown);
    return out;
  }

  function startGcode(g, firstTemp, title, totalLayers, maxZ) {
    const ctx = g.ctx;
    const [values, flags] = templateValues(ctx, firstTemp, title, totalLayers, maxZ);
    g.out('; HEADER_BLOCK_START');
    g.out(text('generated_by', ctx.lang, { version: P.version(), title }));
    g.out(`; total layer number: ${totalLayers}`);
    g.out(`; filament_diameter: ${trim(ctx.p.filament_diameter, 3)}`);
    g.out(`; max_z_height: ${fixed(maxZ, 2)}`);
    g.out('; HEADER_BLOCK_END');
    g.out('');
    g.out('; EXECUTABLE_BLOCK_START');
    const body = expandTemplate(ctx, ctx.p.start_gcode, values, flags);
    for (const s of body) g.out(s);
    const sim = C3D.gcodeSim.endState(body);
    if (!sim.absolute) g.out('G90');
    if (!sim.e_relative_set) g.out('M83');
    const st = ctx.p.start_state || sim;
    g.x = st.x - ctx.ox; g.y = st.y - ctx.oy; g.z = st.z;
    g.time += st.time;
    g.e_total += st.e;
    g.body_start = g.lines.length;
  }

  function endGcode(g, maxZ) {
    const ctx = g.ctx;
    g.body_end = g.lines.length;
    const [values, flags] = templateValues(ctx, 0, '', 0, maxZ);
    for (const s of expandTemplate(ctx, ctx.p.end_gcode, values, flags)) g.out(s);
    g.out('; EXECUTABLE_BLOCK_END');
  }

  function footer(g, title) {
    const grams = g.e_total * g.ctx.FIL_AREA / 1000 * g.mat.density;
    const total = pyRound(g.time / 60);
    const h = Math.floor(total / 60), m = total - h * 60;
    g.out('');
    g.out(`; ${title}`);
    g.out(`; filament used [mm] = ${fixed(g.e_total, 2)}`);
    g.out(`; filament used [g] = ${fixed(grams, 2)}`);
    g.out(`; estimated printing time (normal mode) = ${h}h ${m}m`);
    return grams;
  }

  // ---------- rectangles ----------

  function rectLoop(x1, y1, x2, y2) { return [[x1, y1], [x2, y1], [x2, y2], [x1, y2]]; }

  function perimeters(g, box, w, h, speedOuter, speedInner, n, kind) {
    if (n === undefined) n = 2;
    if (kind === undefined) kind = 'wall';
    const [x1, y1, x2, y2] = box;
    for (let i = n - 1; i >= 0; i--) {
      const o = w / 2 + i * w;
      g.path(rectLoop(x1 + o, y1 + o, x2 - o, y2 - o), w, h, i === 0 ? speedOuter : speedInner, i === 0 ? kind : 'inner', true);
    }
  }

  function fill(g, box, w, h, speed, alongX, spacing, kind, flow) {
    const [x1, y1, x2, y2] = box;
    const lines = [];
    if (alongX) {
      let y = y1 + w / 2;
      while (y <= y2 - w / 2 + 1e-6) { lines.push([[x1, y], [x2, y]]); y += spacing; }
    } else {
      let x = x1 + w / 2;
      while (x <= x2 - w / 2 + 1e-6) { lines.push([[x, y1], [x, y2]]); x += spacing; }
    }
    for (let i = 0; i < lines.length; i++) {
      let [a, b] = lines[i];
      if (i % 2) [a, b] = [b, a];
      if (i === 0) g.travel(a[0], a[1]);
      else g.extrude(a[0], a[1], w, h, speed, kind, flow);
      g.extrude(b[0], b[1], w, h, speed, kind, flow);
    }
  }

  // ---------- seven-segment digits ----------

  const SEGS = { 0: 'abcdef', 1: 'bc', 2: 'abged', 3: 'abgcd', 4: 'fgbc', 5: 'afgcd', 6: 'afgedc', 7: 'abc', 8: 'abcdefg', 9: 'abcdfg' };

  function segBoxes(W, H, S) {
    return { a: [0, W, H - S, H], g: [0, W, (H - S) / 2, (H + S) / 2], d: [0, W, 0, S],
      f: [0, S, H / 2, H], b: [W - S, W, H / 2, H], e: [0, S, 0, H / 2], c: [W - S, W, 0, H / 2] };
  }

  function textIntervals(txt, x0, v, W, H, S, gap) {
    if (W === undefined) { W = 3.6; H = 6.0; S = 1.2; gap = 1.0; }
    const boxes = segBoxes(W, H, S);
    const out = [];
    for (let i = 0; i < txt.length; i++) {
      const dx = x0 + i * (W + gap);
      const spans = [];
      for (const s of SEGS[txt[i]]) {
        const b = boxes[s];
        if (b[2] <= v && v <= b[3]) spans.push([dx + b[0], dx + b[1]]);
      }
      spans.sort((p, q) => (p[0] - q[0]) || (p[1] - q[1]));
      for (const [a, b] of spans) {
        const last = out[out.length - 1];
        if (out.length && a <= last[1] + 1e-6 && last[0] >= dx - 1e-6) out[out.length - 1] = [last[0], Math.max(last[1], b)];
        else out.push([a, b]);
      }
    }
    return out;
  }

  function flatDigitStrokes(ch, x0, y0, W, H) {
    if (W === undefined) { W = 2.0; H = 3.2; }
    const p = { a: [[0, H], [W, H]], g: [[0, H / 2], [W, H / 2]], d: [[0, 0], [W, 0]],
      f: [[0, H / 2], [0, H]], b: [[W, H / 2], [W, H]], e: [[0, 0], [0, H / 2]], c: [[W, 0], [W, H / 2]] };
    const out = [];
    for (const s of 'fabgedc') {
      if (SEGS[ch].indexOf(s) >= 0) out.push([[x0 + p[s][0][0], y0 + p[s][0][1]], [x0 + p[s][1][0], y0 + p[s][1][1]]]);
    }
    return out;
  }

  // ---------- shared by the tests ----------

  function slowLayer(g, start, t0, minTime) {
    const dt = g.time - t0;
    if (0 < dt && dt < minTime) {
      const k = dt / minTime;
      for (let i = start; i < g.lines.length; i++) {
        const s = g.lines[i];
        if (s.startsWith('G1 X') && s.indexOf(' E') >= 0 && s.indexOf(' F') >= 0) {
          const at = s.lastIndexOf(' F');
          const head = s.slice(0, at), f = s.slice(at + 2);
          g.lines[i] = `${head} F${fixed(Math.max(600, parseFloat(f) * k), 0)}`;
        }
      }
      g.time = t0 + minTime;
    }
  }

  function runLayers(g, zs, body, minTime) {
    if (minTime === undefined) minTime = true;
    const total = zs.length;
    let prev = 0.0;
    for (let n = 0; n < zs.length; n++) {
      const z = zs[n];
      const h = z - prev;
      g.layer(n, z, h, total);
      if (n === g.mat.fan_off_layers) g.fan(g.mat.fan);
      const start = g.lines.length, t0 = g.time;
      body(n, z, h);
      if (minTime) slowLayer(g, start, t0, g.mat.min_layer_time);
      prev = z;
    }
  }

  function layersTo(top, h) {
    const n = pyRound(top / h);
    const out = [];
    for (let i = 0; i < n; i++) out.push(pyRound(h * (i + 1), 3));
    return out;
  }

  function inset(box, d) { return [box[0] + d, box[1] + d, box[2] - d, box[3] - d]; }

  function solid(g, box, n, o) {
    o = o || {};
    const w = o.w === undefined ? g.ctx.W : o.w;
    const h = o.h === undefined ? g.ctx.H : o.h;
    const walls = o.walls === undefined ? 2 : o.walls;
    const wallSpeed = o.wall_speed === undefined ? 60 : o.wall_speed;
    const fillSpeed = o.fill_speed === undefined ? 100 : o.fill_speed;
    perimeters(g, box, w, h, wallSpeed, wallSpeed * 1.5, walls, o.kind || 'wall');
    fill(g, inset(box, walls * w - 0.15 * w), w, h, fillSpeed,
      o.along_x === undefined || o.along_x === null ? (n % 2 === 0) : o.along_x, w, 'infill', o.flow);
  }

  function sparse(g, box, n, o) {
    o = o || {};
    const w = o.w === undefined ? g.ctx.W : o.w;
    const h = o.h === undefined ? g.ctx.H : o.h;
    const walls = o.walls === undefined ? 2 : o.walls;
    const wallSpeed = o.wall_speed === undefined ? 60 : o.wall_speed;
    const fillSpeed = o.fill_speed === undefined ? 120 : o.fill_speed;
    const density = o.density === undefined ? 0.2 : o.density;
    perimeters(g, box, w, h, wallSpeed, wallSpeed * 1.5, walls, o.kind || 'wall');
    fill(g, inset(box, walls * w - 0.15 * w), w, h, fillSpeed, n % 2 === 0, w / density, 'infill');
  }

  function emboss(g, txt, x0, yFace, v, o) {
    o = o || {};
    const W_ = o.W_ === undefined ? 3.6 : o.W_;
    const H_ = o.H_ === undefined ? 6.0 : o.H_;
    const S_ = o.S_ === undefined ? 1.2 : o.S_;
    const gap = o.gap === undefined ? 1.0 : o.gap;
    const w = o.w === undefined ? g.ctx.W : o.w;
    const h = o.h === undefined ? g.ctx.H : o.h;
    if (!(0 <= v && v <= H_)) return;
    for (const [a, b] of textIntervals(txt, x0, v, W_, H_, S_, gap)) {
      for (const yy of [yFace - 0.6, yFace - 0.15]) {
        let xa = a + w / 2, xb = b - w / 2;
        if (xb - xa < 0.1) { xa = (a + b) / 2 - 0.05; xb = (a + b) / 2 + 0.05; }
        g.travel(xa, yy, false);
        g.extrude(xb, yy, w, h, 20, 'label');
      }
    }
  }

  function flatText(g, txt, x0, y0, h, Wd, Hd, gap) {
    if (Wd === undefined) { Wd = 2.0; Hd = 3.2; gap = 1.2; }
    for (let j = 0; j < txt.length; j++) {
      for (const [a, b] of flatDigitStrokes(txt[j], x0 + j * (Wd + gap), y0, Wd, Hd)) {
        if (hypot(a[0] - g.x, a[1] - g.y) <= 2) g.travel(a[0], a[1], false);
        else g.travel(a[0], a[1]);
        g.extrude(b[0], b[1], g.ctx.LW, h, 20, 'label');
      }
    }
  }

  function textWidth(txt, Wd, gap) { return txt.length * Wd + (txt.length - 1) * gap; }

  // Only characters every disk takes: the prefix of an own profile is free text.
  function safeName(s) { return String(s).replace(/[^A-Za-z0-9._+-]/g, '_'); }

  function fileName(ctx, test, matName, rng) {
    return safeName(`${ctx.p.prefix}_${trim(ctx.NOZ, 2)}_${test}_${matName}${rng ? '_' + rng : ''}`) + '.gcode';
  }

  class Result {
    constructor(g, name, title, grams, maxZ) {
      this.g = g; this.name = name; this.title = title; this.grams = grams; this.max_z = maxZ;
    }
    get text() { return this.g.lines.join('\n') + '\n'; }
    get time() { return this.g.time; }
  }

  function finish(g, name, title, maxZ) {
    endGcode(g, maxZ);
    const grams = footer(g, title);
    return new Result(g, name, title, grams, maxZ);
  }

  // ---------- temperature tower ----------

  function tempTower(ctx, prm) {
    const m = ctx.m;
    const g = new Gcode(ctx);
    g.fixed_temp = true;
    const H = ctx.H, W = ctx.W;
    const t0 = prm.t_start, t1 = prm.t_end, step = prm.t_step;
    const temps = [];
    if (t0 > t1) for (let t = t0; t > t1 - 1; t -= step) temps.push(t);
    else for (let t = t0; t < t1 + 1; t += step) temps.push(t);
    const layersPerLevel = pyRound(10.0 / H);
    const LEVEL = pyRound(layersPerLevel * H, 3);
    const SLAB = 1.6;
    const nBase = Math.max(1, pyRound(0.6 / H));
    const BASE = pyRound(nBase * H, 3);
    const A = [104.0, 123.0, 118.0, 133.0];
    const B = [138.0, 123.0, 152.0, 133.0];
    const slabBox = [A[0], A[1], B[2], B[3]];
    const baseBox = [96.0, 116.0, 160.0, 140.0];
    const total = nBase + layersPerLevel * temps.length;
    const maxZ = BASE + LEVEL * temps.length;
    const title = text('temp_tower', ctx.lang, { mat: m.type, t0: String(temps[0]), t1: String(temps[temps.length - 1]) });
    startGcode(g, temps[0], title, total, maxZ);
    const outer = 60, inner = 100, infill = 120;
    let n = 0;
    for (let i = 0; i < nBase; i++) {
      const z = H * (i + 1);
      g.layer(n, z, H, total);
      const w = i === 0 ? ctx.W1 : W;
      const sp = i === 0 ? 40 : infill;
      perimeters(g, baseBox, w, H, i === 0 ? 40 : outer, sp, 2, 'base');
      const o = 2 * w;
      fill(g, [baseBox[0] + o - 0.15 * w, baseBox[1] + o - 0.15 * w, baseBox[2] - o + 0.15 * w, baseBox[3] - o + 0.15 * w],
        w, H, sp, i % 2 === 0, w, 'base');
      n += 1;
    }
    for (let lvl = 0; lvl < temps.length; lvl++) {
      const t = temps[lvl];
      g.out(text('tower_level', ctx.lang, { n: String(lvl + 1), t: String(t) }));
      g.out(`M104 S${t}`);
      const label = String(t);
      for (let k = 0; k < layersPerLevel; k++) {
        const z = BASE + lvl * LEVEL + H * (k + 1);
        const local = H * (k + 1);
        g.layer(n, z, H, total);
        if (n === m.fan_off_layers) g.fan(m.fan);
        const layerStart = g.lines.length;
        const tStart = g.time;
        if (local <= LEVEL - SLAB + 1e-6) {
          for (const [box, hasLabel] of [[A, true], [B, false]]) {
            perimeters(g, box, W, H, outer, inner);
            if (hasLabel) {
              const v = local - H / 2 - 1.8;
              if (0 <= v && v <= 6.0) {
                const x0 = A[0] + (14.0 - (label.length * 3.6 + (label.length - 1) * 1.0)) / 2;
                for (const [a, b] of textIntervals(label, x0, v)) {
                  for (const yy of [A[1] - 0.6, A[1] - 0.15]) {
                    let xa = a + W / 2, xb = b - W / 2;
                    if (xb - xa < 0.1) { xa = (a + b) / 2 - 0.05; xb = (a + b) / 2 + 0.05; }
                    g.travel(xa, yy, false);
                    g.extrude(xb, yy, W, H, 20, 'label');
                  }
                }
              }
            }
            const o = 2 * W - 0.15 * W;
            fill(g, [box[0] + o, box[1] + o, box[2] - o, box[3] - o], W, H, infill, k % 2 === 0, W / 0.2, 'infill');
          }
        } else {
          const firstSlab = local - (LEVEL - SLAB) <= H + 1e-6;
          if (firstSlab) g.fan(m.bridge_fan);
          perimeters(g, slabBox, W, H, firstSlab ? 30 : outer, firstSlab ? 30 : inner, 2, 'slab');
          const o = 2 * W - 0.15 * W;
          fill(g, [slabBox[0] + o, slabBox[1] + o, slabBox[2] - o, slabBox[3] - o], W, H,
            firstSlab ? 30 : infill, firstSlab || k % 2 === 0, W, firstSlab ? 'bridge' : 'slab');
          if (firstSlab && n >= m.fan_off_layers) g.fan(m.fan);
        }
        slowLayer(g, layerStart, tStart, m.min_layer_time);
        n += 1;
      }
    }
    const name = fileName(ctx, 'TempTower', m.type, `${temps[0]}-${temps[temps.length - 1]}`);
    return finish(g, name, title, maxZ);
  }

  // ---------- pressure advance lines ----------

  function paLines(ctx, prm) {
    const m = ctx.m;
    const g = new Gcode(ctx);
    const H = ctx.H, W = ctx.W1;
    const count = pyRound((prm.pa_end - prm.pa_start) / prm.pa_step) + 1;
    const values = [];
    for (let i = 0; i < count; i++) values.push(pyRound(prm.pa_start + i * prm.pa_step, 3));
    const xStart = 60.0, slowLen = 20.0, fastLen = 40.0;
    const y0 = 60.0, step = 5.0;
    const total = 2;
    const title = text('pa_lines', ctx.lang, { mat: m.type, v0: fixed(values[0], 3), v1: fixed(values[values.length - 1], 3) });
    startGcode(g, m.first_layer_temp, title, total, 2 * H);
    const fast = Math.min(150.0, m.mvs * 0.9 / area(W, H));
    const slow = 20.0;
    g.layer(0, H, H, total);
    g.out(`M104 S${m.nozzle_temp}`);
    g.fixed_temp = true;
    const frame = [xStart - 6, y0 - 6, xStart + 2 * slowLen + fastLen + 24, y0 + step * (values.length - 1) + 6];
    perimeters(g, frame, W, H, 30, 30, 2, 'base');
    const xEnd = xStart + 2 * slowLen + fastLen;
    for (let i = 0; i < values.length; i++) {
      const v = values[i];
      const y = y0 + i * step;
      g.retract();
      g.travel(xStart, y);
      g.pressureAdvance(v);
      g.out('M400');
      g.extrude(xStart + slowLen, y, W, H, slow, 'slow', 1.0);
      g.extrude(xStart + slowLen + fastLen, y, W, H, fast, 'fast', 1.0);
      g.extrude(xEnd, y, W, H, slow, 'slow', 1.0);
    }
    g.pressureAdvance(m.pa_default, text('pa_restore', ctx.lang));
    for (const layer of [0, 1]) {
      if (layer === 1) g.layer(1, 2 * H, H, total);
      for (let i = 0; i < values.length; i++) {
        const y = y0 + i * step - 1.6;
        const txt = String(pyRound(values[i] * 1000)).padStart(3, '0');
        for (let j = 0; j < txt.length; j++) {
          for (const [a, b] of flatDigitStrokes(txt[j], xEnd + 5 + j * 3.2, y)) {
            if (hypot(a[0] - g.x, a[1] - g.y) <= 2) g.travel(a[0], a[1], false);
            else g.travel(a[0], a[1]);
            g.extrude(b[0], b[1], ctx.LW, H, 20, 'label');
          }
        }
      }
    }
    const name = fileName(ctx, 'PressureAdvance_Lines', m.type, `${trim(values[0], 3)}-${fixed(values[values.length - 1], 3)}`);
    return finish(g, name, title, 2 * H);
  }

  // ---------- flow ----------

  function flowTest(ctx, prm) {
    const m = ctx.m;
    const g = new Gcode(ctx);
    const W = ctx.W, W1 = ctx.W1;
    const pcts = [];
    for (let i = 0; i < 9; i++) pcts.push(prm.f_start + i * prm.f_step);
    const boxes = [];
    for (let i = 0; i < pcts.length; i++) {
      const cx = 94 + (i % 3) * 34;
      const cy = 167 - Math.floor(i / 3) * 36;
      boxes.push([[cx - 11, cy - 11, cx + 11, cy + 11], pcts[i]]);
    }
    const zs = layersTo(1.2, ctx.H);
    const title = text('flow', ctx.lang, { mat: m.type, p0: String(pcts[0]), p1: String(pcts[pcts.length - 1]) });
    startGcode(g, m.first_layer_temp, title, zs.length, zs[zs.length - 1]);
    runLayers(g, zs, (n, z, h) => {
      const w = n === 0 ? W1 : W;
      for (const [box, p] of boxes) {
        const flow = m.flow * p / 100;
        perimeters(g, box, w, h, n === 0 ? 40 : 60, n === 0 ? 40 : 90, 2);
        fill(g, inset(box, 2 * w - 0.15 * w), w, h, n === 0 ? 40 : 80,
          n % 2 === 0 || n === zs.length - 1, w, n === zs.length - 1 ? 'top' : 'infill', flow);
        if (n < 2) {
          const txt = String(p);
          flatText(g, txt, (box[0] + box[2]) / 2 - textWidth(txt, 2.0, 1.2) / 2, box[1] - 6, h);
        }
      }
    });
    return finish(g, fileName(ctx, 'Flow', m.type, `${pcts[0]}-${pcts[pcts.length - 1]}`), title, zs[zs.length - 1]);
  }

  // ---------- retraction ----------

  function retractionTest(ctx, prm) {
    const m = ctx.m;
    const g = new Gcode(ctx);
    const W = ctx.W, W1 = ctx.W1;
    const values = [];
    for (let i = 0; i < prm.r_count; i++) values.push(pyRound(prm.r_start + i * prm.r_step, 3));
    const LEVEL = 5.0, BASE = 0.6;
    const A = [96.0, 124.0, 108.0, 132.0];
    const B = [148.0, 124.0, 160.0, 132.0];
    const baseBox = [92.0, 120.0, 164.0, 136.0];
    const zs = layersTo(BASE + LEVEL * values.length, ctx.H);
    const title = text('retraction', ctx.lang, { mat: m.type, v0: trim(values[0], 2), v1: trim(values[values.length - 1], 2) });
    startGcode(g, m.first_layer_temp, title, zs.length, zs[zs.length - 1]);
    runLayers(g, zs, (n, z, h) => {
      if (z <= BASE + 1e-6) {
        solid(g, baseBox, n, { w: n === 0 ? W1 : W, h, wall_speed: 40 });
        return;
      }
      const lvl = Math.min(Math.trunc((z - BASE - 1e-6) / LEVEL), values.length - 1);
      if (g.retract_len !== values[lvl]) {
        g.out(text('retraction_level', ctx.lang, { n: String(lvl + 1), v: pyRepr(values[lvl]) }));
        g.retract_len = values[lvl];
      }
      const local = z - BASE - lvl * LEVEL;
      for (const box of [A, B]) {
        sparse(g, box, n, { h });
        if (box === A) {
          const txt = String(pyRound(values[lvl] * 10)).padStart(2, '0');
          emboss(g, txt, A[0] + (12 - textWidth(txt, 2.6, 0.8)) / 2, A[1], local - h / 2 - 0.7,
            { W_: 2.6, H_: 3.6, S_: 0.9, gap: 0.8 });
        }
      }
    });
    return finish(g, fileName(ctx, 'Retraction', m.type, `${trim(values[0], 2)}-${trim(values[values.length - 1], 2)}`), title, zs[zs.length - 1]);
  }

  // ---------- max volumetric flow ----------

  function maxFlowTest(ctx, prm) {
    const m = ctx.m;
    const g = new Gcode(ctx);
    const W1 = ctx.W1, WW = ctx.WW, HH = ctx.HH;
    let v0 = prm.v_start, v1 = prm.v_end;
    const limit = ctx.MAX_SPEED * area(WW, HH);
    if (v1 > limit) v1 = Math.floor(limit);
    const low = 5.0 * area(WW, HH);
    if (v0 < low) v0 = Math.ceil(low);
    if (v1 < v0 + 4) v1 = v0 + 4;
    const box = [78.0, 118.0, 178.0, 138.0];
    const BASE = pyRound(2 * ctx.H, 3);
    const zs = layersTo(BASE, ctx.H);
    const nUp = pyRound((v1 - v0) / HH);
    for (let i = 0; i < nUp; i++) zs.push(pyRound(BASE + HH * (i + 1), 3));
    const title = text('max_flow', ctx.lang, { mat: m.type, v0: fixed(v0, 0), v1: fixed(v1, 0) });
    startGcode(g, m.first_layer_temp, title, zs.length, zs[zs.length - 1]);
    g.accel(Math.min(10000, ctx.p.max_accel));
    runLayers(g, zs, (n, z, h) => {
      if (z <= BASE + 1e-6) {
        solid(g, box, n, { w: W1, h, wall_speed: 40, fill_speed: 60 });
        return;
      }
      const vol = v0 + (z - BASE);
      const speed = vol / area(WW, HH);
      const o = WW / 2;
      const loop = [[box[0] + o, box[1] + o], [box[2] - o, box[1] + o], [box[2] - o, box[3] - o], [box[0] + o, box[3] - o]];
      g.travel(loop[0][0], loop[0][1]);
      for (const p of loop.slice(1).concat(loop.slice(0, 1))) g.extrude(p[0], p[1], WW, HH, speed, 'wall', 1.0, false);
      for (let mark = Math.trunc(v0) + 4; mark < Math.trunc(v1); mark += 4) {
        const v = (z - BASE) - (mark - v0) - HH / 2;
        if (0 <= v && v <= 3.0) emboss(g, String(mark), box[0] + 4, box[1], v, { W_: 2.2, H_: 3.0, S_: 0.8, gap: 0.7, h: HH });
      }
    }, false);
    return finish(g, fileName(ctx, 'MaxFlow', m.type, `${fixed(v0, 0)}-${fixed(v1, 0)}`), title, zs[zs.length - 1]);
  }

  // ---------- overhangs and bridges ----------

  function overhangBridgeTest(ctx, prm) {
    const m = ctx.m;
    const g = new Gcode(ctx);
    const W1 = ctx.W1;
    const angles = [20, 30, 40, 50, 60, 70, 80];
    const spine = [60.0, 170.0, 134.0, 176.0];
    const spineBase = [58.0, 168.0, 136.0, 178.0];
    const finZ0 = 1.0, topOv = 16.0;
    const lengths = [10, 20, 30, 40, 50];
    const rows = lengths.map((_, i) => [60.0 + 0, 60.0 + i * 18]);
    const PILLAR_H = 8.0, SLAB = 1.0;
    const zs = layersTo(topOv, ctx.H);
    const title = text('overhang', ctx.lang, { mat: m.type, a0: String(angles[0]), a1: String(angles[angles.length - 1]),
      l0: String(lengths[0]), l1: String(lengths[lengths.length - 1]) });
    startGcode(g, m.first_layer_temp, title, zs.length, zs[zs.length - 1]);
    runLayers(g, zs, (n, z, h) => {
      const w = n === 0 ? W1 : ctx.W;
      if (z <= finZ0 + 1e-6) solid(g, spineBase, n, { w, h, wall_speed: 40 });
      else {
        sparse(g, spine, n, { h });
        for (let i = 0; i < angles.length; i++) {
          const d = Math.min(12.0, (z - finZ0) * tanDeg(angles[i]));
          if (d >= 1.0) {
            const x = 62.0 + i * 10;
            solid(g, [x, spine[1] - d, x + 8, spine[1] + 0.5], n, { h, wall_speed: 40, fill_speed: 60 });
          }
        }
      }
      if (n < 2) {
        for (let i = 0; i < angles.length; i++) {
          const a = String(angles[i]);
          flatText(g, a, 62.0 + i * 10 + 4 - textWidth(a, 2.0, 1.2) / 2, spine[1] - 18, h);
        }
      }
      for (let i = 0; i < rows.length; i++) {
        const [x0, y0] = rows[i];
        const L = lengths[i];
        const left = [x0, y0, x0 + 6, y0 + 8];
        const right = [x0 + 6 + L, y0, x0 + 12 + L, y0 + 8];
        if (z <= PILLAR_H + 1e-6) {
          for (const p of [left, right]) solid(g, p, n, { w, h, wall_speed: n === 0 ? 40 : 60 });
        } else if (z <= PILLAR_H + SLAB + 1e-6) {
          const first = z - PILLAR_H <= h + 1e-6;
          if (first) g.fan(m.bridge_fan);
          const slab = [x0, y0, x0 + 12 + L, y0 + 8];
          solid(g, slab, n, { h, wall_speed: first ? 30 : 60, fill_speed: first ? 30 : 80,
            along_x: first ? true : null, kind: first ? 'bridge' : 'slab' });
          if (first && n >= m.fan_off_layers) g.fan(m.fan);
        }
        if (n < 2) flatText(g, String(L), x0 + 12 + L + 4, y0 + 2.4, h);
      }
    });
    return finish(g, fileName(ctx, 'OverhangBridge', m.type), title, zs[zs.length - 1]);
  }

  // ---------- first layer ----------

  function firstLayerTest(ctx, prm) {
    const m = ctx.m;
    const g = new Gcode(ctx);
    const H = ctx.H;
    const zs = [H];
    const title = text('first_layer', ctx.lang, { mat: m.type });
    startGcode(g, m.first_layer_temp, title, 1, H);
    const bed = ctx.p.bed;
    let xs, ys;
    if (bed.shape === 'round') {
      const r = Math.min(bed.x, bed.y) / 2;
      const s = (r - 4) / Math.sqrt(2) - 17;
      xs = [128.0 - s, 128.0, 128.0 + s];
      ys = xs.slice();
    } else {
      let loX = -ctx.ox, loY = -ctx.oy;
      if (bed.origin === 'center') { loX = loX - bed.x / 2; loY = loY - bed.y / 2; }
      xs = [loX + 34, loX + bed.x / 2, loX + bed.x - 34];
      ys = [loY + 34, loY + bed.y / 2, loY + bed.y - 34];
    }
    runLayers(g, zs, (n, z, h) => {
      for (const cy of ys) {
        for (const cx of (cy !== ys[0] ? xs : xs.slice().reverse())) {
          solid(g, [cx - 17, cy - 17, cx + 17, cy + 17], 0, { w: ctx.W1, h, wall_speed: 40, fill_speed: 50 });
        }
      }
    }, false);
    return finish(g, fileName(ctx, 'FirstLayer', m.type), title, H);
  }

  // ---------- tolerances ----------

  function toleranceTest(ctx, prm) {
    const m = ctx.m;
    const g = new Gcode(ctx);
    const gaps = prm.gaps.slice();
    const PEG = 8.0;
    const zs = layersTo(6.0, ctx.H);
    const title = text('tolerance', ctx.lang, { mat: m.type, g0: fixed(gaps[0], 2), g1: fixed(gaps[gaps.length - 1], 2) });
    startGcode(g, m.first_layer_temp, title, zs.length, zs[zs.length - 1]);
    const xFirst = 128.0 - (gaps.length - 1) * 11;
    runLayers(g, zs, (n, z, h) => {
      const w = ctx.W;
      const sp = n === 0 ? 30 : 60;
      for (let i = 0; i < gaps.length; i++) {
        const gap = gaps[i];
        const cx = xFirst + i * 22, cy = 128.0;
        const outer = [cx - 9, cy - 9, cx + 9, cy + 9];
        const hole = [cx - PEG / 2 - gap, cy - PEG / 2 - gap, cx + PEG / 2 + gap, cy + PEG / 2 + gap];
        const peg = [cx - PEG / 2, cy - PEG / 2, cx + PEG / 2, cy + PEG / 2];
        perimeters(g, outer, w, h, sp, sp * 1.5, 2);
        for (let k = 0; k < 2; k++) {
          const o = w / 2 + k * w;
          g.path(rectLoop(hole[0] - o, hole[1] - o, hole[2] + o, hole[3] + o), w, h, sp, k === 0 ? 'wall' : 'inner', true);
        }
        const a = inset(outer, 2 * w - 0.15 * w), b = inset(hole, -(2 * w - 0.15 * w));
        for (const strip of [[a[0], a[1], a[2], b[1]], [a[0], b[3], a[2], a[3]], [a[0], b[1], b[0], b[3]], [b[2], b[1], a[2], b[3]]]) {
          if (strip[2] - strip[0] > w && strip[3] - strip[1] > w) fill(g, strip, w, h, sp, n % 2 === 0, w, 'infill');
        }
        solid(g, peg, n, { w, h, wall_speed: sp, fill_speed: sp });
        if (n < 2) {
          const txt = String(pyRound(gap * 100)).padStart(2, '0');
          flatText(g, txt, cx - textWidth(txt, 2.0, 1.2) / 2, outer[1] - 6, h);
        }
      }
    });
    return finish(g, fileName(ctx, 'Tolerance', m.type, `${fixed(gaps[0], 2)}-${fixed(gaps[gaps.length - 1], 2)}`), title, zs[zs.length - 1]);
  }

  // ---------- cube ----------

  function cubeTest(ctx, prm) {
    const m = ctx.m;
    const g = new Gcode(ctx);
    const size = prm.size;
    const half = size / 2;
    const box = [128.0 - half, 128.0 - half, 128.0 + half, 128.0 + half];
    const zs = layersTo(size, ctx.H);
    const bottom = Math.max(3, pyRound(0.8 / ctx.H));
    const top = Math.max(4, pyRound(1.0 / ctx.H));
    const label = String(size);
    const title = text('cube', ctx.lang, { mat: m.type, s: label });
    startGcode(g, m.first_layer_temp, title, zs.length, zs[zs.length - 1]);
    runLayers(g, zs, (n, z, h) => {
      const w = n === 0 ? ctx.W1 : ctx.W;
      if (n < bottom || n >= zs.length - top) solid(g, box, n, { w, h, walls: 3, wall_speed: n === 0 ? 40 : 60 });
      else sparse(g, box, n, { h, walls: 3 });
      emboss(g, label, box[0] + (size - textWidth(label, 3.6, 1.0)) / 2, box[1], z - h / 2 - (size / 2 - 3.0));
    });
    return finish(g, fileName(ctx, `Cube${label}`, m.type), title, zs[zs.length - 1]);
  }

  // ---------- ringing ----------

  function ringingTest(ctx, prm) {
    const m = ctx.m;
    const g = new Gcode(ctx);
    const W = ctx.W, H = ctx.H;
    const box = [98.0, 98.0, 158.0, 158.0];
    const BAND = 5.0, BASE = 0.6;
    let accels = [];
    for (let i = 0; i < prm.a_count; i++) accels.push(prm.a_start + prm.a_step * i);
    accels = accels.filter((a) => a <= ctx.p.max_accel);
    if (!accels.length) accels = [Math.min(prm.a_start, ctx.p.max_accel)];
    const speed = Math.min(150.0, m.mvs * 0.9 / area(W, H));
    const zs = layersTo(BASE + BAND * accels.length, H);
    const title = text('ringing', ctx.lang, { mat: m.type, a0: String(accels[0]), a1: String(accels[accels.length - 1]) });
    startGcode(g, m.first_layer_temp, title, zs.length, zs[zs.length - 1]);
    runLayers(g, zs, (n, z, h) => {
      if (z <= BASE + 1e-6) {
        solid(g, box, n, { w: n === 0 ? ctx.W1 : W, h, wall_speed: 40 });
        return;
      }
      const band = Math.min(Math.trunc((z - BASE - 1e-6) / BAND), accels.length - 1);
      const local = z - BASE - band * BAND;
      if (local <= h + 1e-6) {
        g.out(text('ringing_band', ctx.lang, { n: String(band + 1), a: String(accels[band]) }));
        g.accel(accels[band], true);
      }
      perimeters(g, box, W, h, speed, speed, 2);
      emboss(g, String(band + 1), box[0] + 6, box[1], local - h / 2 - 0.7, { W_: 2.6, H_: 3.6, S_: 0.9, gap: 0.8 });
    }, false);
    const rng = `${trim(accels[0] / 1000, 1)}k-${trim(accels[accels.length - 1] / 1000, 1)}k`;
    return finish(g, fileName(ctx, 'Ringing', m.type, rng), title, zs[zs.length - 1]);
  }

  // ---------- the list ----------

  const BUILDERS = {
    first_layer: firstLayerTest,
    temp_tower: tempTower,
    flow: flowTest,
    pressure_advance: paLines,
    retraction: retractionTest,
    max_flow: maxFlowTest,
    overhang_bridge: overhangBridgeTest,
    ringing: ringingTest,
    tolerance: toleranceTest,
    cube: cubeTest,
  };
  const TEST_IDS = Object.keys(BUILDERS);

  function defaultParams(testId, material) {
    const t = material.tower;
    return {
      first_layer: {},
      temp_tower: { t_start: t.start, t_end: t.end, t_step: t.step },
      flow: { f_start: 80, f_step: 5 },
      pressure_advance: { pa_start: 0.0, pa_end: 0.08, pa_step: 0.005 },
      retraction: { r_start: 0.2, r_step: 0.2, r_count: 8 },
      max_flow: { v_start: material.max_flow[0], v_end: material.max_flow[1] },
      overhang_bridge: {},
      ringing: { a_start: 1000, a_step: 1000, a_count: 12 },
      tolerance: { gaps: [0.1, 0.15, 0.2, 0.25, 0.3, 0.4] },
      cube: { size: 20 },
    }[testId];
  }

  function bounds(ctx, g) {
    let x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity;
    for (const s of g.segments) {
      x1 = Math.min(x1, s[0], s[2]); x2 = Math.max(x2, s[0], s[2]);
      y1 = Math.min(y1, s[1], s[3]); y2 = Math.max(y2, s[1], s[3]);
    }
    return [ctx.px(x1), ctx.py(y1), ctx.px(x2), ctx.py(y2)];
  }

  function fits(printer, box, margin) {
    if (margin === undefined) margin = 1.0;
    const bed = printer.bed;
    const [x1, y1, x2, y2] = box;
    if (bed.shape === 'round') {
      const r = Math.min(bed.x, bed.y) / 2 - margin;
      return [[x1, y1], [x1, y2], [x2, y1], [x2, y2]].every(([x, y]) => hypot(x, y) <= r);
    }
    let loX, loY, hiX, hiY;
    if (bed.origin === 'center') { loX = -bed.x / 2; loY = -bed.y / 2; hiX = bed.x / 2; hiY = bed.y / 2; }
    else { loX = 0.0; loY = 0.0; hiX = bed.x; hiY = bed.y; }
    return x1 >= loX + margin && y1 >= loY + margin && x2 <= hiX - margin && y2 <= hiY - margin;
  }

  function generate(printer, material, testId, params, lang) {
    printer = P.normalizePrinter(printer);
    material = P.normalizeMaterial(material);
    let prm = Object.assign(defaultParams(testId, material), params || {});
    if (C3D.params) {
      prm = C3D.params.normalize(testId, prm);
      const errors = C3D.params.validate(testId, prm, printer, material);
      if (errors.length) throw new ParamError(errors);
    }
    const build = BUILDERS[testId];
    let ctx = new Ctx(printer, material, lang || 'ru');
    let res = build(ctx, prm);
    const box = bounds(ctx, res.g);
    if (fits(printer, box)) return res;
    const bed = printer.bed;
    const cx = bed.origin === 'center' ? 0.0 : bed.x / 2;
    const cy = bed.origin === 'center' ? 0.0 : bed.y / 2;
    const shift = [cx - (box[0] + box[2]) / 2, cy - (box[1] + box[3]) / 2];
    ctx = new Ctx(printer, material, lang || 'ru', shift);
    res = build(ctx, prm);
    if (!fits(printer, bounds(ctx, res.g))) throw new DoesNotFit(testId + ': does not fit the bed');
    return res;
  }

  const api = { generate, defaultParams, TEST_IDS, BUILDERS, Ctx, Gcode, area, templateValues, firmwareCommands,
    purgeGeometry, text, TemplateError, DoesNotFit, ParamError, parkPoint, safeName, fits, bounds, layersTo };
  C3D.generator = api;
  if (isNode) module.exports = api;
})();
