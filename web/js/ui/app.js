// The page: the same 4-step wizard as the Qt window (printer, material, tests, download)
// plus the result helper. Everything runs here, nothing is sent anywhere. In Electron the
// preload adds window.calib3dDesktop (save to a folder); in a browser files are downloaded.
(function () {
  'use strict';
  const C3D = window.C3D;
  const G = C3D.generator, P = C3D.profiles, PR = C3D.params;
  const THEMES = ['glass', 'formal', 'light', 'night', 'warm'];
  const STEPS = ['step_printer', 'step_material', 'step_tests', 'step_download', 'step_results'];
  const BASES = { klipper: 'generic-klipper', marlin: 'generic-marlin', rrf: 'generic-rrf' };
  const desktop = window.calib3dDesktop || null;

  // ---------- storage (may be blocked: then nothing is remembered, nothing breaks) ----------
  const store = {
    get(key, def) { try { const v = localStorage.getItem(key); return v === null ? def : JSON.parse(v); } catch (e) { return def; } },
    set(key, v) { try { localStorage.setItem(key, JSON.stringify(v)); } catch (e) { /* ignore */ } },
  };
  const clone = (x) => JSON.parse(JSON.stringify(x));

  // ---------- state ----------
  const S = {
    lang: 'ru', theme: 'glass', step: 0, printer: null, material: null, selected: G.TEST_IDS.slice(), params: {},
    imported: null, importReport: null, results: {}, round: 0, current: 'first_layer', view3d: null,
  };

  function myPrinters() { return store.get('calib3d-printers', []).filter((p) => p && p.id); }
  function myMaterials() { return store.get('calib3d-materials', []).filter((m) => m && m.id); }
  function allPrinters() { return P.printers().concat(myPrinters().map((p) => Object.assign(p, { _user: true })), S.imported ? [S.imported.printer] : []); }
  function allMaterials() { return P.materials().concat(myMaterials().map((m) => Object.assign(m, { _user: true })), S.imported ? [S.imported.material] : []); }
  function findPrinter(id) { const p = allPrinters().find((x) => x.id === id); return p ? clone(p) : null; }
  function findMaterial(id) { const m = allMaterials().find((x) => x.id === id); return m ? clone(m) : null; }
  const strip = (o) => { const c = clone(o); for (const k of Object.keys(c)) if (k.startsWith('_')) delete c[k]; return c; };

  function load() {
    const s = store.get('calib3d-settings', {});
    const nav = (navigator.language || 'en').toLowerCase();
    S.lang = s.lang === 'ru' || s.lang === 'en' ? s.lang : (nav.startsWith('ru') ? 'ru' : 'en');
    const th = store.get('calib3d-theme', null);
    S.theme = THEMES.indexOf(th) >= 0 ? th : 'glass';
    S.printer = findPrinter(s.printer_id) || findPrinter('elegoo-centauri-carbon');
    S.material = findMaterial(s.material_id) || findMaterial('petg');
    if (Array.isArray(s.selected)) S.selected = G.TEST_IDS.filter((t) => s.selected.indexOf(t) >= 0);
    if (s.params && typeof s.params === 'object') S.params = s.params;
  }

  function save() {
    store.set('calib3d-settings', { lang: S.lang, printer_id: S.printer.id, material_id: S.material.id, selected: S.selected, params: S.params });
    store.set('calib3d-theme', S.theme);
  }

  function testParams(tid) { return Object.assign(G.defaultParams(tid, S.material), S.params[tid] || {}); }

  // ---------- text ----------
  function t(key, vals) {
    const e = C3D.data.ui_text[key];
    let s = e ? (e[S.lang] || e.en) : key;
    for (const k of Object.keys(vals || {})) s = s.split('{' + k + '}').join(String(vals[k]));
    return s;
  }
  function fmtTime(min) {
    const h = Math.floor(min / 60), m = min - h * 60;
    return h ? t('hours_minutes', { h, m }) : t('only_minutes', { m });
  }

  // ---------- DOM helper ----------
  function h(tag, props) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(props || {})) {
      if (v === undefined || v === null || v === false) continue;
      if (k === 'class') el.className = v;
      else if (k === 'text') el.textContent = v;
      else if (k.startsWith('on')) el.addEventListener(k.slice(2), v);
      else if (k === 'value') el.value = v;
      else el.setAttribute(k, v === true ? '' : v);
    }
    for (let i = 2; i < arguments.length; i++) {
      const c = arguments[i];
      for (const x of (Array.isArray(c) ? c : [c])) if (x !== null && x !== undefined && x !== false) el.appendChild(typeof x === 'string' ? document.createTextNode(x) : x);
    }
    return el;
  }
  const $ = (id) => document.getElementById(id);

  function getPath(d, path) { return path.split('.').reduce((o, k) => (o === undefined || o === null ? undefined : o[k]), d); }
  function setPath(d, path, v) {
    const parts = path.split('.');
    let o = d;
    for (const k of parts.slice(0, -1)) o = (o[k] = o[k] || {});
    o[parts[parts.length - 1]] = v;
  }

  // ---------- theme and language ----------
  function applyTheme() {
    if (S.theme === 'glass') document.documentElement.removeAttribute('data-theme');
    else document.documentElement.setAttribute('data-theme', S.theme);
    if (S.step === 2) redrawViews();
  }

  function frame() {
    document.documentElement.lang = S.lang;
    document.title = t('app_title');
    $('title').textContent = t('app_title');
    $('subtitle').textContent = t('app_sub') + '  ·  ' + t('version', { v: C3D.data.version });
    $('theme-label').textContent = t('theme');
    $('lang-label').textContent = t('language');
    const th = $('theme');
    th.innerHTML = '';
    for (const id of THEMES) th.appendChild(h('option', { value: id, text: t('theme_' + id) }));
    th.value = S.theme;
    $('lang').value = S.lang;
    const nav = $('steps');
    nav.innerHTML = '';
    STEPS.forEach((key, i) => {
      if (i === 4) nav.appendChild(h('span', { class: 'spacer' }));
      nav.appendChild(h('button', { type: 'button', class: 'step', role: 'tab', 'data-step': i, text: t(key), onclick: () => go(i) }));
    });
    $('back').textContent = t('back');
    $('next').textContent = t('next');
  }

  function render() {
    frame();
    const main = $('pages');
    main.innerHTML = '';
    main.appendChild(printerPage());
    main.appendChild(materialPage());
    main.appendChild(testsPage());
    main.appendChild(downloadPage());
    main.appendChild(resultsPage());
    S.view3d = null;
    go(S.step);
    recompute();
  }

  function go(i) {
    S.step = Math.max(0, Math.min(STEPS.length - 1, i));
    document.querySelectorAll('.page').forEach((p, k) => { p.hidden = k !== S.step; });
    document.querySelectorAll('.step').forEach((b) => {
      const on = +b.getAttribute('data-step') === S.step;
      b.classList.toggle('active', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    $('back').disabled = S.step === 0;
    $('next').hidden = S.step >= 3;
    if (S.step === 2) showTest(S.current);
    if (S.step === 3) fillDownload();
  }

  // ---------- form fields ----------
  function field(target, path, kind, opts, onChange) {
    opts = opts || {};
    let el;
    const v = getPath(target(), path);
    if (kind === 'select') {
      el = h('select', { 'data-path': path });
      for (const [val, label] of opts.items) el.appendChild(h('option', { value: String(val), text: label }));
      el.value = String(v);
      el.addEventListener('change', () => {
        const item = opts.items.find(([val]) => String(val) === el.value);
        setPath(target(), path, item ? item[0] : el.value);
        onChange(path, el);
      });
    } else if (kind === 'check') {
      el = h('input', { type: 'checkbox', 'data-path': path });
      el.checked = !!v;
      el.addEventListener('change', () => { setPath(target(), path, el.checked); onChange(path, el); });
    } else if (kind === 'code') {
      el = h('textarea', { 'data-path': path, spellcheck: 'false', rows: 14, wrap: 'off' });
      el.value = (v || []).join('\n');
      el.addEventListener('change', () => { setPath(target(), path, el.value.split('\n')); onChange(path, el); });
    } else if (kind === 'text') {
      el = h('input', { type: 'text', 'data-path': path, value: v === undefined ? '' : String(v) });
      el.addEventListener('change', () => { setPath(target(), path, el.value); onChange(path, el); });
    } else {
      // A text field, not type=number: Chromium shows numbers with the system's decimal
      // comma whatever the page says, and G-code numbers have a dot. A comma typed in is
      // read as a dot.
      el = h('input', { type: 'text', inputmode: 'decimal', 'data-path': path, value: v === undefined ? '' : String(v) });
      el.addEventListener('change', () => {
        const raw = el.value.replace(',', '.');
        const n = opts.int ? parseInt(raw, 10) : parseFloat(raw);
        setPath(target(), path, Number.isFinite(n) ? n : el.value);
        onChange(path, el);
      });
    }
    return el;
  }

  function grid(rows, prefix) {
    const g = h('div', { class: 'grid' });
    for (const [label, el] of rows) {
      const id = prefix + el.getAttribute('data-path').replace(/\./g, '-');
      el.id = id;
      g.appendChild(h('label', { class: 'dim', for: id, text: label }));
      g.appendChild(el);
    }
    return g;
  }

  // ---------- printer ----------
  function printerPage() {
    const page = h('section', { class: 'page', id: 'page-printer' });
    const file = h('input', { type: 'file', id: 'gcode-file', accept: '.gcode,.gco,.g,text/plain', hidden: true,
      onchange: () => { if (file.files[0]) readImport(file.files[0]); } });
    const drop = h('div', { class: 'card import', id: 'import-card' },
      h('div', { class: 'import-text' }, h('h2', { text: t('import_title') }), h('p', { class: 'dim', text: t('import_hint') })),
      h('button', { type: 'button', class: 'big', id: 'import-button', text: t('import_button'), onclick: () => file.click() }), file,
      h('pre', { class: 'report', id: 'import-report', hidden: !S.importReport }));
    drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('over'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('over'));
    drop.addEventListener('drop', (e) => {
      e.preventDefault();
      drop.classList.remove('over');
      if (e.dataTransfer.files[0]) readImport(e.dataTransfer.files[0]);
    });
    page.appendChild(drop);
    // Anywhere else a dropped file would open in place of the page (a browser does that, and
    // Electron too): only the import card takes files.
    if (!document.__dropGuard) {
      document.__dropGuard = true;
      document.addEventListener('dragover', (e) => e.preventDefault());
      document.addEventListener('drop', (e) => e.preventDefault());
    }

    const sel = h('select', { id: 'printer-select', onchange: () => { S.printer = findPrinter(sel.value); save(); render(); } });
    for (const p of allPrinters()) sel.appendChild(h('option', { value: p.id, text: (p.verified ? '✓ ' : '') + p.name + (p._user ? `  (${t('my_profile')})` : '') }));
    sel.value = S.printer.id;
    const p = S.printer;
    const warn = [];
    if (!p.verified) warn.push(t('unverified_hint'));
    if (p.warning && String(p.id).startsWith('bambu')) warn.push(t('import_bambu'));
    if (p.source) warn.push(t('source') + ': ' + p.source);
    const jsonIn = h('input', { type: 'file', accept: '.json,application/json', hidden: true, onchange: () => { if (jsonIn.files[0]) importJson(jsonIn.files[0]); } });
    page.appendChild(h('div', { class: 'card' },
      h('div', { class: 'row' }, h('label', { class: 'section', for: 'printer-select', text: t('profile') }), sel,
        h('span', { class: p.verified ? 'badge ok' : 'badge warn', id: 'printer-badge', text: p.verified ? '✓ ' + t('verified') : '⚠ ' + t('unverified') })),
      h('p', { class: 'hint', id: 'printer-warning', text: warn.join('\n') }),
      h('div', { class: 'row' },
        h('button', { type: 'button', id: 'save-printer', text: t('save_profile'), onclick: savePrinter }),
        h('button', { type: 'button', id: 'delete-printer', text: t('delete_profile'), disabled: !p._user, onclick: deletePrinter }),
        h('button', { type: 'button', id: 'export-json', text: t('export_json'), onclick: exportJson }),
        h('button', { type: 'button', id: 'import-json', text: t('import_json'), onclick: () => jsonIn.click() }), jsonIn),
      h('p', { class: 'error', id: 'printer-status' })));

    const tgt = () => S.printer;
    const ch = (path, el) => { el.classList.remove('missing'); validatePrinter(); save(); schedule(); };
    const num = (path, step, int) => field(tgt, path, 'number', { step, int }, ch);
    const rows = [
      [t('name'), field(tgt, 'name', 'text', {}, ch)], [t('prefix'), field(tgt, 'prefix', 'text', {}, ch)],
      [t('bed_x'), num('bed.x', 1)], [t('bed_y'), num('bed.y', 1)], [t('bed_z'), num('bed.z', 1)],
      [t('origin'), field(tgt, 'bed.origin', 'select', { items: [['corner', t('origin_corner')], ['center', t('origin_center')]] }, ch)],
      [t('shape'), field(tgt, 'bed.shape', 'select', { items: [['rect', t('shape_rect')], ['round', t('shape_round')]] }, ch)],
      [t('nozzle'), num('nozzle', 0.05)],
      [t('filament'), field(tgt, 'filament_diameter', 'select', { items: [[1.75, '1.75'], [2.85, '2.85']] }, ch)],
      [t('firmware'), field(tgt, 'firmware', 'select', { items: [['klipper', 'Klipper'], ['marlin', 'Marlin'], ['rrf', 'RepRapFirmware']] }, ch)],
      [t('max_speed'), num('max_speed', 10)], [t('max_accel'), num('max_accel', 100, true)],
      [t('default_accel'), num('default_accel', 100, true)], [t('travel_speed'), num('travel_speed', 10)],
      [t('z_speed'), num('z_speed', 1)], [t('retract_length'), num('retract.length', 0.1)],
      [t('retract_speed'), num('retract.speed', 1)], [t('z_hop'), num('retract.z_hop', 0.1)],
    ];
    const opts = h('div', { class: 'row' });
    const o = p.options || {};
    if ('canvas' in o) opts.appendChild(h('label', { class: 'check' }, field(tgt, 'options.canvas', 'check', {}, ch), ' ' + t('opt_canvas')));
    if ('nozzle_wipe' in o) opts.appendChild(h('label', { class: 'check' }, field(tgt, 'options.nozzle_wipe', 'check', {}, ch), ' ' + t('opt_nozzle_wipe')));
    page.appendChild(h('div', { class: 'card', id: 'printer-form' }, h('h2', { text: t('section_bed') }), grid(rows, 'f-'), opts));
    page.appendChild(h('div', { class: 'card' }, h('h2', { text: t('section_code') }), h('p', { class: 'hint', text: t('placeholders_hint') }),
      h('div', { class: 'codes' },
        h('label', { class: 'dim' }, t('start_code'), field(tgt, 'start_gcode', 'code', {}, ch)),
        h('label', { class: 'dim' }, t('end_code'), field(tgt, 'end_gcode', 'code', {}, ch)))));
    setTimeout(() => { markMissing(); validatePrinter(); showReport(); }, 0);
    return page;
  }

  function validatePrinter() {
    const errs = P.validatePrinter(strip(S.printer));
    const el = $('printer-status');
    if (el) el.textContent = errs.length ? t('profile_errors', { errors: errs.slice(0, 4).join('; ') }) : '';
    return errs;
  }

  function markMissing() {
    const miss = S.importReport && S.printer.id === 'imported' ? S.importReport.missing : [];
    document.querySelectorAll('#page-printer [data-path]').forEach((el) => {
      el.classList.toggle('missing', miss.indexOf(el.getAttribute('data-path')) >= 0);
    });
  }

  function showReport() {
    const r = S.importReport;
    const el = $('import-report');
    if (!el || !r) return;
    const lines = [t('import_done', { file: r.file, slicer: r.slicer || '?' }), t('import_replaced', { n: r.replaced.length })];
    for (const rep of r.replaced.slice(0, 8)) lines.push(`   ${rep.before}  →  ${rep.after}`);
    lines.push(r.missing.length ? t('import_missing', { fields: r.missing.join(', ') }) : t('import_all_found'));
    if (r.warnings.indexOf('bambu') >= 0) lines.push(t('import_bambu'));
    if (r.warnings.indexOf('firmware_unknown') >= 0) lines.push(t('import_fw_unknown'));
    el.textContent = lines.join('\n');
    el.hidden = false;
  }

  function importText(text, name) {
    const r = C3D.importer.parse(text, name);
    const fw = r.printer.firmware || S.printer.firmware || 'marlin';
    const base = P.printer(BASES[fw] || 'generic-marlin');
    const mtype = (r.material.type || '').toLowerCase();
    const baseMat = findMaterial(mtype) || clone(S.material);
    const [printer, material] = C3D.importer.toProfiles(r, base, baseMat);
    S.imported = { printer: clone(printer), material: clone(material) };
    S.importReport = r;
    S.printer = printer;
    S.material = material;
    save();
    render();
    return r;
  }

  function readImport(file) {
    const reader = new FileReader();
    reader.onload = () => importText(String(reader.result), file.name);
    reader.onerror = () => { const el = $('import-report'); el.textContent = t('import_failed', { error: reader.error }); el.hidden = false; };
    reader.readAsText(file);
  }

  function savePrinter() {
    if (validatePrinter().length) return;
    const p = strip(S.printer);
    p.id = 'my-' + (p.name || 'profile').trim().toLowerCase().replace(/[^a-z0-9._-]+/g, '-').replace(/^-+|-+$/g, '');
    const list = myPrinters().filter((x) => x.id !== p.id);
    list.push(p);
    store.set('calib3d-printers', list);
    S.printer = findPrinter(p.id);
    save();
    render();
    $('printer-status').textContent = t('saved', { name: p.name });
  }

  function deletePrinter() {
    if (!S.printer._user) return;
    store.set('calib3d-printers', myPrinters().filter((x) => x.id !== S.printer.id));
    S.printer = findPrinter('elegoo-centauri-carbon');
    save();
    render();
  }

  function downloadBlob(name, data, type) {
    const blob = data instanceof Blob ? data : new Blob([data], { type: type || 'application/octet-stream' });
    const a = h('a', { href: URL.createObjectURL(blob), download: name });
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }

  function exportJson() {
    const name = (S.printer.name || 'printer').toLowerCase().replace(/[^a-z0-9._-]+/g, '-') + '.json';
    downloadBlob(name, JSON.stringify(strip(S.printer), null, 2), 'application/json');
  }

  function importJson(file) {
    const reader = new FileReader();
    reader.onload = () => {
      let data = null;
      try { data = JSON.parse(String(reader.result)); } catch (e) { data = null; }
      const errs = data ? P.validatePrinter(data) : ['not a profile'];
      if (errs.length) { $('printer-status').textContent = t('profile_errors', { errors: errs.slice(0, 4).join('; ') }); return; }
      S.printer = data;
      savePrinter();
    };
    reader.readAsText(file);
  }

  // ---------- material ----------
  function materialPage() {
    const page = h('section', { class: 'page', id: 'page-material' });
    const sel = h('select', { id: 'material-select', onchange: () => { S.material = findMaterial(sel.value); save(); render(); } });
    for (const m of allMaterials()) sel.appendChild(h('option', { value: m.id, text: (m.verified ? '✓ ' : '') + m.name + (m._user ? `  (${t('my_profile')})` : '') }));
    sel.value = S.material.id;
    const m = S.material;
    page.appendChild(h('div', { class: 'card' },
      h('div', { class: 'row' }, h('label', { class: 'section', for: 'material-select', text: t('material') }), sel,
        h('span', { class: m.verified ? 'badge ok' : 'badge', text: m.verified ? '✓ ' + t('mat_verified') : t('mat_generic') })),
      h('div', { class: 'row' }, h('button', { type: 'button', id: 'save-material', text: t('save_profile'), onclick: saveMaterial })),
      h('p', { class: 'error', id: 'material-status' })));
    const tgt = () => S.material;
    const ch = () => { validateMaterial(); save(); schedule(); };
    const num = (path, step, int) => field(tgt, path, 'number', { step, int }, ch);
    page.appendChild(h('div', { class: 'card' }, grid([
      [t('name'), field(tgt, 'name', 'text', {}, ch)], [t('mat_type'), field(tgt, 'type', 'text', {}, ch)],
      [t('nozzle_temp'), num('nozzle_temp', 1, true)], [t('first_layer_temp'), num('first_layer_temp', 1, true)],
      [t('bed_temp'), num('bed', 1, true)], [t('tower_start'), num('tower.start', 5, true)],
      [t('tower_end'), num('tower.end', 5, true)], [t('tower_step'), num('tower.step', 1, true)],
      [t('flow'), num('flow', 0.01)], [t('mvs'), num('mvs', 0.5)], [t('fan'), num('fan', 0.05)],
      [t('bridge_fan'), num('bridge_fan', 0.05)], [t('fan_off_layers'), num('fan_off_layers', 1, true)],
      [t('min_layer_time'), num('min_layer_time', 0.5)], [t('pa_default'), num('pa_default', 0.001)],
      [t('density'), num('density', 0.01)], [t('max_flow_from'), num('max_flow.0', 0.5)], [t('max_flow_to'), num('max_flow.1', 0.5)],
    ], 'm-')));
    setTimeout(validateMaterial, 0);
    return page;
  }

  function validateMaterial() {
    const errs = P.validateMaterial(strip(S.material));
    const el = $('material-status');
    if (el) el.textContent = errs.length ? t('profile_errors', { errors: errs.slice(0, 4).join('; ') }) : '';
    return errs;
  }

  function saveMaterial() {
    if (validateMaterial().length) return;
    const m = strip(S.material);
    m.id = 'my-' + (m.name || 'material').trim().toLowerCase().replace(/[^a-z0-9._-]+/g, '-').replace(/^-+|-+$/g, '');
    store.set('calib3d-materials', myMaterials().filter((x) => x.id !== m.id).concat([m]));
    S.material = findMaterial(m.id);
    save();
    render();
  }

  // ---------- generation ----------
  let timer = null;
  function schedule() { clearTimeout(timer); timer = setTimeout(recompute, 250); }

  function runOne(tid) {
    try {
      const res = G.generate(strip(S.printer), strip(S.material), tid, testParams(tid), S.lang);
      return { ok: true, res, summary: PR.summary(res), problems: C3D.check.checkResult(res, tid), preview: C3D.preview.previewData(res) };
    } catch (e) {
      return { ok: false, error: e.kind === 'does_not_fit' ? 'does_not_fit' : e.message };
    }
  }

  function recompute() {
    const rnd = ++S.round;
    S.results = {};
    const order = [S.current].concat(G.TEST_IDS.filter((x) => x !== S.current));
    let i = 0;
    const step = () => {
      if (rnd !== S.round || i >= order.length) return;
      const tid = order[i++];
      S.results[tid] = runOne(tid);
      updateTestRow(tid);
      if (tid === S.current && S.step === 2) showResult(tid);
      updateTotals();
      if (S.step === 3) fillDownload();
      setTimeout(step, 0);
    };
    G.TEST_IDS.forEach(updateTestRow);
    setTimeout(step, 0);
  }

  // ---------- tests ----------
  function testsPage() {
    const page = h('section', { class: 'page', id: 'page-tests' });
    const list = h('ul', { class: 'tests', id: 'test-list' });
    for (const info of PR.tests()) {
      const cb = h('input', { type: 'checkbox', 'data-test': info.id, 'aria-label': info.name[S.lang] });
      cb.checked = S.selected.indexOf(info.id) >= 0;
      cb.addEventListener('change', () => {
        S.selected = G.TEST_IDS.filter((x) => (x === info.id ? cb.checked : S.selected.indexOf(x) >= 0));
        save();
        updateTotals();
      });
      list.appendChild(h('li', { 'data-test': info.id, class: info.id === S.current ? 'current' : '', onclick: (e) => { if (e.target !== cb) showTest(info.id); } },
        cb, h('span', { class: 'name', text: info.name[S.lang] }), h('span', { class: 'meta dim', 'data-meta': info.id, text: '…' })));
    }
    const all = (on) => { S.selected = on ? G.TEST_IDS.slice() : []; save(); list.querySelectorAll('input').forEach((c) => { c.checked = on; }); updateTotals(); };
    page.appendChild(h('div', { class: 'tests-layout' },
      h('div', { class: 'tests-left' }, h('p', { class: 'dim', text: t('tests_hint') }), list,
        h('div', { class: 'row' }, h('button', { type: 'button', id: 'select-all', text: t('select_all'), onclick: () => all(true) }),
          h('button', { type: 'button', id: 'select-none', text: t('select_none'), onclick: () => all(false) })),
        h('p', { class: 'hint', id: 'tests-total' })),
      h('div', { class: 'tests-right' },
        h('div', { class: 'card' }, h('h2', { id: 'test-title', class: 'title' }), h('p', { id: 'test-look' }), h('p', { id: 'test-where', class: 'dim' }),
          h('p', { id: 'test-fast', class: 'error', text: t('fast_warning'), hidden: true })),
        h('div', { class: 'card', id: 'test-params' }),
        h('div', { class: 'card' }, h('p', { id: 'test-info', class: 'big' }), h('p', { id: 'test-check', class: 'hint' }),
          h('div', { class: 'views' },
            h('figure', { id: 'box-top' }, h('figcaption', { class: 'dim', text: t('preview_top') }), h('canvas', { id: 'view-top' })),
            h('figure', { id: 'box-front' }, h('figcaption', { class: 'dim', text: t('preview_front') }), h('canvas', { id: 'view-front' }))),
          h('figure', { id: 'box-3d', class: 'box3d' }, h('figcaption', { class: 'dim' }, t('preview_3d') + ' · ', h('label', { for: 'layer-slider', text: t('layer_upto') + ' ' }),
            h('input', { type: 'range', id: 'layer-slider', min: 1, max: 1, value: 1 }), h('span', { id: 'layer-value' })),
          h('div', { id: 'view-3d', class: 'view3d' }))))));
    return page;
  }

  function updateTestRow(tid) {
    const el = document.querySelector(`[data-meta="${tid}"]`);
    if (!el) return;
    const out = S.results[tid];
    if (!out) el.textContent = '…';
    else if (!out.ok) el.textContent = '⚠';
    else el.textContent = `${fmtTime(out.summary.minutes)} · ${out.summary.grams} ${t('grams')}${out.problems.length ? '  ⚠' : ''}`;
  }

  function totals() {
    let min = 0, grams = 0;
    for (const tid of S.selected) {
      const o = S.results[tid];
      if (o && o.ok) { min += o.summary.minutes; grams += parseFloat(o.summary.grams); }
    }
    return t('total', { n: S.selected.length, time: fmtTime(min), grams: grams.toFixed(0) });
  }

  function updateTotals() {
    const el = $('tests-total');
    if (el) el.textContent = totals();
  }

  function showTest(tid) {
    S.current = tid;
    document.querySelectorAll('#test-list li').forEach((li) => li.classList.toggle('current', li.getAttribute('data-test') === tid));
    const info = PR.testInfo(tid);
    $('test-title').textContent = info.name[S.lang];
    $('test-look').textContent = t('look_for') + ': ' + info.look[S.lang];
    $('test-where').textContent = t('result_where') + ': ' + info.result[S.lang];
    $('test-fast').hidden = !info.fast;
    buildParams(tid);
    showResult(tid);
  }

  function buildParams(tid) {
    const box = $('test-params');
    box.innerHTML = '';
    const info = PR.testInfo(tid);
    box.hidden = !info.params.length;
    if (!info.params.length) return;
    box.appendChild(h('h2', { text: t('params') }));
    const prm = testParams(tid);
    const row = h('div', { class: 'params' });
    const err = h('p', { class: 'error', id: 'param-error' });
    for (const spec of info.params) {
      let input;
      if (spec.type === 'list') {
        input = h('input', { type: 'text', 'data-param': spec.key, value: prm[spec.key].map((v) => v.toFixed(spec.digits || 2)).join(' ') });
      } else {
        input = h('input', { type: 'text', inputmode: spec.type === 'int' ? 'numeric' : 'decimal', 'data-param': spec.key, value: String(prm[spec.key]) });
      }
      input.addEventListener('change', () => {
        let v;
        if (spec.type === 'list') v = input.value.split(/\s+/).filter(Boolean).map((x) => C3D.num.pyRound(parseFloat(x.replace(',', '.')), 3));
        else if (spec.type === 'int') v = parseInt(input.value, 10);
        else v = C3D.num.pyRound(parseFloat(input.value.replace(',', '.')), spec.digits || 3);
        S.params[tid] = Object.assign({}, S.params[tid] || {}, { [spec.key]: v });
        const errs = PR.validate(tid, testParams(tid), S.printer, S.material);
        err.textContent = errs.join('; ');
        save();
        if (!errs.length) schedule();
      });
      const id = 'p-' + spec.key;
      input.id = id;
      row.appendChild(h('div', {}, h('label', { class: 'dim', for: id, text: spec.label[S.lang] }), input));
    }
    box.appendChild(row);
    box.appendChild(err);
  }

  function redrawViews() {
    const out = S.results[S.current];
    const data = out && out.ok ? out.preview : null;
    const top = $('view-top'), front = $('view-front');
    if (top) C3D.views.draw2d(top, data, 'top');
    if (front) C3D.views.draw2d(front, data, 'front');
    if (S.view3d) S.view3d.render();
  }

  function showResult(tid) {
    const out = S.results[tid];
    const info = $('test-info'), chk = $('test-check');
    if (!info) return;
    if (!out) { info.textContent = t('computing'); chk.textContent = ''; redrawViews(); return; }
    if (!out.ok) {
      info.textContent = t('gen_error', { error: out.error === 'does_not_fit' ? t('does_not_fit') : out.error });
      chk.textContent = '';
      redrawViews();
      return;
    }
    info.textContent = out.summary.name + '\n' + t('time_grams', { time: fmtTime(out.summary.minutes), grams: out.summary.grams });
    chk.className = out.problems.length ? 'error' : 'ok';
    chk.textContent = out.problems.length ? t('check_failed', { problems: out.problems.slice(0, 3).join('; ') }) : '✓ ' + t('check_ok');
    $('box-front').hidden = !out.preview.front;
    redrawViews();
    // 3D
    if (!S.view3d) S.view3d = new C3D.views.View3D($('view-3d'));
    if (!S.view3d.ok) { $('box-3d').hidden = true; return; }
    S.view3d.set(C3D.preview.layers(out.res));
    const slider = $('layer-slider');
    const n = S.view3d.layerZs.length;
    slider.max = String(n);
    slider.value = String(n);
    $('layer-value').textContent = `${n} / ${n}`;
    slider.oninput = () => { S.view3d.showUpTo(+slider.value); $('layer-value').textContent = `${slider.value} / ${n}`; };
  }

  // ---------- download ----------
  function downloadPage() {
    const page = h('section', { class: 'page', id: 'page-download' });
    const buttons = desktop
      ? [h('button', { type: 'button', class: 'primary', id: 'save-folder', text: t('save_folder'), onclick: saveFolder }),
        h('button', { type: 'button', id: 'save-zip', text: t('save_zip'), onclick: saveZip })]
      : [h('button', { type: 'button', class: 'primary', id: 'download-zip', text: t('download_zip'), onclick: downloadZip })];
    page.appendChild(h('div', { class: 'card' }, h('p', { class: 'dim', text: t('download_hint') }), h('div', { class: 'row' }, buttons),
      h('p', { class: 'ok', id: 'download-status' }), h('p', { class: 'hint', text: t('watch_first') })));
    page.appendChild(h('div', { class: 'card' }, h('h2', { text: t('print_order') }),
      h('div', { class: 'table-wrap' }, h('table', { id: 'order' }, h('thead', {}, h('tr', {},
        ['col_n', 'col_file', 'col_time', 'col_look', 'col_result', ''].map((k) => h('th', { text: k ? t(k) : '' })))), h('tbody', {}))),
      h('p', { class: 'hint', id: 'download-total' })));
    return page;
  }

  function fillDownload() {
    const body = document.querySelector('#order tbody');
    if (!body) return;
    body.innerHTML = '';
    S.selected.forEach((tid, i) => {
      const info = PR.testInfo(tid);
      const o = S.results[tid];
      const name = o && o.ok ? o.summary.name : info.name[S.lang];
      const btn = o && o.ok ? h('button', { type: 'button', class: 'small', 'data-download': tid, text: t('download_one'), onclick: () => downloadOne(tid) }) : '';
      body.appendChild(h('tr', {}, h('td', { text: String(i + 1) }), h('td', { class: 'mono', text: name }),
        h('td', { text: o && o.ok ? fmtTime(o.summary.minutes) : '…' }), h('td', { text: info.look[S.lang] }),
        h('td', { text: info.result[S.lang] }), h('td', {}, btn)));
    });
    $('download-total').textContent = totals();
    document.querySelectorAll('#download-zip, #save-folder, #save-zip').forEach((b) => { b.disabled = !S.selected.length; });
  }

  function files() {
    const out = [];
    for (const tid of S.selected) {
      let o = S.results[tid];
      if (!o) { o = runOne(tid); S.results[tid] = o; }
      if (o.ok) out.push({ name: o.summary.name, text: o.res.text });
    }
    return out;
  }

  function downloadOne(tid) {
    const o = S.results[tid];
    if (o && o.ok) downloadBlob(o.summary.name, o.res.text, 'text/plain');
  }

  function zipName() { return `${S.printer.prefix || 'calib'}_${S.material.type || ''}_calibration.zip`; }

  async function downloadZip() {
    const fs = files();
    const bytes = await C3D.zip.makeZip(fs);
    downloadBlob(zipName(), bytes, 'application/zip');
    $('download-status').textContent = t('saved_files', { n: fs.length, path: zipName() });
    return fs.map((f) => f.name);
  }

  async function saveFolder() {
    const fs = files();
    const r = await desktop.saveFolder(fs);
    if (r && r.path) $('download-status').textContent = t('saved_files', { n: r.count, path: r.path });
    return r;
  }

  async function saveZip() {
    const fs = files();
    const bytes = await C3D.zip.makeZip(fs);
    const r = await desktop.saveZip(zipName(), bytes);
    if (r && r.path) $('download-status').textContent = t('saved_files', { n: fs.length, path: r.path });
    return r;
  }

  // ---------- result helper ----------
  function resultsPage() {
    const page = h('section', { class: 'page', id: 'page-results' });
    page.appendChild(h('p', { class: 'dim', text: t('results_hint') }));
    PR.tests().forEach((info, i) => {
      const card = h('div', { class: 'card', 'data-helper': info.id }, h('h2', { text: `${i + 1}. ${info.name[S.lang]}` }), h('p', { text: info.look[S.lang] }));
      if (info.helper) {
        const out = h('p', { class: 'big', 'data-helper-out': info.id });
        const id = 'h-' + info.id;
        const input = h('input', { type: 'text', id, 'data-helper-in': info.id });
        input.addEventListener('input', () => {
          if (!input.value.trim()) { out.textContent = ''; return; }
          const r = PR.helper(info.id, input.value, S.printer, S.material, testParams(info.id));
          out.textContent = r.ok ? t(r.note, { value: r.value }) : t(r.error);
        });
        card.appendChild(h('div', { class: 'row' }, h('label', { class: 'dim', for: id, text: info.helper.input[S.lang] }), input));
        card.appendChild(out);
      } else {
        card.appendChild(h('p', { class: 'dim', text: info.result[S.lang] }));
      }
      page.appendChild(card);
    });
    return page;
  }

  // ---------- start ----------
  function start() {
    load();
    applyTheme();
    $('theme').addEventListener('change', (e) => { S.theme = e.target.value; save(); applyTheme(); });
    $('lang').addEventListener('change', (e) => { S.lang = e.target.value; save(); render(); });
    $('back').addEventListener('click', () => go(S.step - 1));
    $('next').addEventListener('click', () => go(S.step + 1));
    window.addEventListener('resize', () => { if (S.step === 2) redrawViews(); });
    render();
  }

  // For tests and the desktop shell: read-only access to the state and a few actions.
  window.calib3dApp = {
    state: S, go, importText, files, downloadZip, saveFolder, saveZip, showTest, recompute,
    done: () => G.TEST_IDS.every((tid) => S.results[tid]),
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
