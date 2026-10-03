// Previews: top and front views on a 2D canvas (like the Qt window), and a 3D view of all
// layers with three.js (lines coloured by kind, "up to layer N" slider). The 3D view turns
// with the mouse (drag) and zooms with the wheel; it never asks for pointer lock.
(function () {
  'use strict';
  const root = typeof globalThis !== 'undefined' ? globalThis : window;
  const C3D = root.C3D || (root.C3D = {});
  const COLORS = () => C3D.preview.COLORS;

  function css(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  /** Draw a top or front view of preview data on a canvas. */
  function draw2d(canvas, data, mode) {
    const dpr = window.devicePixelRatio || 1;
    const w = canvas.clientWidth || 320, h = canvas.clientHeight || 220;
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
    const g = canvas.getContext('2d');
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    g.clearRect(0, 0, w, h);
    const light = document.documentElement.getAttribute('data-theme') === 'light';
    g.fillStyle = light ? '#f4f6fa' : '#1c1e24';
    g.beginPath();
    if (g.roundRect) g.roundRect(0.5, 0.5, w - 1, h - 1, 10); else g.rect(0.5, 0.5, w - 1, h - 1);
    g.fill();
    if (!data) return;
    const bed = data.bed;
    const segs = mode === 'top' ? data.top : (data.front || []);
    let x0, y0, x1, y1;
    if (mode === 'top') {
      if (bed.origin === 'center') { x0 = -bed.x / 2; y0 = -bed.y / 2; x1 = bed.x / 2; y1 = bed.y / 2; }
      else { x0 = 0; y0 = 0; x1 = bed.x; y1 = bed.y; }
    } else {
      if (!segs.length) return;
      x0 = Infinity; x1 = -Infinity; y1 = 0;
      for (const s of segs) { x0 = Math.min(x0, s[0], s[2]); x1 = Math.max(x1, s[0], s[2]); y1 = Math.max(y1, s[1]); }
      x0 -= 5; x1 += 5; y0 = 0; y1 += 5;
    }
    const pad = 10;
    const sc = Math.min((w - 2 * pad) / (x1 - x0), (h - 2 * pad) / (y1 - y0));
    const ox = pad + ((w - 2 * pad) - sc * (x1 - x0)) / 2;
    const oy = pad + ((h - 2 * pad) - sc * (y1 - y0)) / 2;
    const X = (x) => ox + (x - x0) * sc, Y = (y) => oy + (y1 - y) * sc;
    g.strokeStyle = light ? '#b9c0cc' : '#3a3f4b';
    g.lineWidth = 1;
    if (mode === 'top') {
      g.beginPath();
      if (bed.shape === 'round') g.ellipse(X(0), Y(0), bed.x / 2 * sc, bed.y / 2 * sc, 0, 0, Math.PI * 2);
      else g.rect(X(x0), Y(y1), (x1 - x0) * sc, (y1 - y0) * sc);
      g.stroke();
    } else {
      g.beginPath(); g.moveTo(X(x0), Y(0)); g.lineTo(X(x1), Y(0)); g.stroke();
    }
    g.lineWidth = Math.max(1, Math.min(2, sc * 0.45));
    const colors = COLORS();
    let current = null;
    for (const s of segs) {
      const c = colors[s[4]] || '#ffffff';
      if (c !== current) {
        if (current) g.stroke();
        g.strokeStyle = c;
        g.beginPath();
        current = c;
      }
      g.moveTo(X(s[0]), Y(s[1]));
      g.lineTo(X(s[2]), Y(s[3]));
    }
    if (current) g.stroke();
  }

  /** 3D view: one LineSegments with vertex colours; segments sorted by height. */
  class View3D {
    constructor(container) {
      this.container = container;
      this.ok = typeof THREE !== 'undefined';
      this.theta = -0.45; this.phi = 0.75; this.dist = 1;
      this.layerZs = [];
      if (!this.ok) return;
      try {
        this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
      } catch (e) {
        this.ok = false;
        return;
      }
      this.scene = new THREE.Scene();
      this.camera = new THREE.PerspectiveCamera(40, 1, 0.5, 5000);
      container.appendChild(this.renderer.domElement);
      const el = this.renderer.domElement;
      el.className = 'view3d-canvas';
      let drag = null;
      el.addEventListener('pointerdown', (e) => { drag = [e.clientX, e.clientY, this.theta, this.phi]; el.setPointerCapture(e.pointerId); });
      el.addEventListener('pointermove', (e) => {
        if (!drag) return;
        this.theta = drag[2] - (e.clientX - drag[0]) * 0.01;
        this.phi = Math.max(0.05, Math.min(1.5, drag[3] - (e.clientY - drag[1]) * 0.01));
        this.render();
      });
      el.addEventListener('pointerup', () => { drag = null; });
      el.addEventListener('wheel', (e) => {
        e.preventDefault();
        this.dist = Math.max(0.2, Math.min(4, this.dist * (e.deltaY > 0 ? 1.12 : 0.89)));
        this.render();
      }, { passive: false });
    }

    set(segments) {
      if (!this.ok) return;
      if (this.lines) { this.scene.remove(this.lines); this.lines.geometry.dispose(); this.lines.material.dispose(); }
      const segs = segments.slice().sort((a, b) => a[4] - b[4]);
      const pos = new Float32Array(segs.length * 6);
      const col = new Float32Array(segs.length * 6);
      const colors = COLORS();
      const cache = {};
      this.layerZs = [];
      this.layerEnds = [];
      let lastZ = null;
      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity, maxZ = 0;
      segs.forEach((s, i) => {
        if (s[4] !== lastZ) {
          if (lastZ !== null) this.layerEnds.push(i);
          this.layerZs.push(s[4]);
          lastZ = s[4];
        }
        pos.set([s[0], s[4], -s[1], s[2], s[4], -s[3]], i * 6);
        const c = cache[s[5]] || (cache[s[5]] = new THREE.Color(colors[s[5]] || '#ffffff'));
        col.set([c.r, c.g, c.b, c.r, c.g, c.b], i * 6);
        minX = Math.min(minX, s[0], s[2]); maxX = Math.max(maxX, s[0], s[2]);
        minY = Math.min(minY, s[1], s[3]); maxY = Math.max(maxY, s[1], s[3]); maxZ = Math.max(maxZ, s[4]);
      });
      this.layerEnds.push(segs.length);
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
      geo.setAttribute('color', new THREE.BufferAttribute(col, 3));
      this.lines = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ vertexColors: true }));
      this.scene.add(this.lines);
      this.center = new THREE.Vector3((minX + maxX) / 2, maxZ / 2, -(minY + maxY) / 2);
      this.size = Math.max(maxX - minX, maxY - minY, maxZ, 20);
      this.showUpTo(this.layerZs.length);
    }

    showUpTo(n) {
      if (!this.ok || !this.lines) return;
      const end = n >= this.layerEnds.length ? this.layerEnds[this.layerEnds.length - 1] : this.layerEnds[Math.max(0, n - 1)];
      this.lines.geometry.setDrawRange(0, end * 2);
      this.render();
    }

    render() {
      if (!this.ok || !this.lines) return;
      const w = this.container.clientWidth || 400, h = this.container.clientHeight || 300;
      this.renderer.setPixelRatio(window.devicePixelRatio || 1);
      this.renderer.setSize(w, h, false);
      const dark = document.documentElement.getAttribute('data-theme') !== 'light';
      this.renderer.setClearColor(dark ? 0x1c1e24 : 0xf4f6fa, 1);
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      const r = this.size * 2.1 * this.dist;
      this.camera.position.set(this.center.x + r * Math.cos(this.phi) * Math.sin(this.theta), this.center.y + r * Math.sin(this.phi),
        this.center.z + r * Math.cos(this.phi) * Math.cos(this.theta));
      this.camera.lookAt(this.center);
      this.renderer.render(this.scene, this.camera);
    }
  }

  C3D.views = { draw2d, View3D, css };
})();
