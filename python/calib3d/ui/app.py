"""The window: a 4-step wizard (printer, material, tests, download) plus the result helper.

Every step is also a tab one can go back to. The core (calib3d.core) does all the work;
this module only shows it. Generation runs in a background thread, debounced, so typing in
a field never freezes the window.
"""
import copy
import json
import sys
import threading
import zipfile
from pathlib import Path

from PySide6.QtCore import QLocale, QObject, Qt, QTimer, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (QAbstractSpinBox, QApplication, QButtonGroup, QCheckBox, QDoubleSpinBox,
                               QFileDialog, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMainWindow, QPlainTextEdit, QPushButton,
                               QScrollArea, QSizePolicy, QSpinBox, QStackedWidget, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from ..core import check as C
from ..core import generator as G
from ..core import importer as I
from ..core import params as PR
from ..core import preview as PV
from ..core import profiles as P
from . import storage, theme
from .i18n import default_lang, tr
from .preview import PreviewView
from .theme import Combo
from .window_state import WindowMemory

STEPS = ["step_printer", "step_material", "step_tests", "step_download", "step_results"]
WINDOW_OPTS = {"width": 1180, "height": 800, "minWidth": 900, "minHeight": 620}
BASES = {"klipper": "generic-klipper", "marlin": "generic-marlin", "rrf": "generic-rrf"}


def fmt_time(minutes, lang):
    h, m = divmod(int(minutes), 60)
    return tr("hours_minutes", lang, h=h, m=m) if h else tr("only_minutes", lang, m=m)


def wrap_label(text="", obj=None):
    """A label that wraps. Never a fixed or maximum height: on a real screen text is a bit
    wider than offscreen and a second line must have room (qt-wrapped-label-height)."""
    lab = QLabel(text)
    lab.setWordWrap(True)
    lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    if obj:
        lab.setObjectName(obj)
    lab.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
    return lab


def card(obj="card"):
    f = QFrame()
    f.setObjectName(obj)
    lay = QVBoxLayout(f)
    lay.setContentsMargins(16, 14, 16, 14)
    lay.setSpacing(10)
    return f, lay


def scroll(widget):
    s = QScrollArea()
    s.setWidgetResizable(True)
    s.setWidget(widget)
    s.setFrameShape(QFrame.Shape.NoFrame)
    return s


def _key(d, part):
    return int(part) if isinstance(d, list) else part


def get_path(d, path):
    for part in path.split("."):
        d = d[_key(d, part)]
    return d


def set_path(d, path, value):
    parts = path.split(".")
    for part in parts[:-1]:
        d = d[_key(d, part)] if isinstance(d, list) else d.setdefault(part, {})
    d[_key(d, parts[-1])] = value


class State(QObject):
    """Everything the user chose; pages read it and change it."""
    changed = Signal(str)

    def __init__(self):
        super().__init__()
        s = storage.load_json(storage.settings_path(), {}) or {}
        self.theme = s.get("theme") if s.get("theme") in theme.THEMES else theme.DEFAULT
        self.lang = s.get("lang") if s.get("lang") in ("ru", "en") else default_lang()
        self.out_dir = s.get("out_dir") or str(Path.home())
        self.reload_profiles()
        self.printer = self.find_printer(s.get("printer_id")) or self.find_printer("elegoo-centauri-carbon")
        self.material = self.find_material(s.get("material_id")) or self.find_material("petg")
        sel = s.get("selected")
        self.selected = [t for t in G.TEST_IDS if sel is None or t in sel]
        self.params = {}
        for tid, prm in (s.get("params") or {}).items():
            if tid in G.TEST_IDS and isinstance(prm, dict):
                self.params[tid] = prm
        self.import_report = None
        self.imported_printer = None
        self.imported_material = None

    def reload_profiles(self):
        self.printers = P.printers() + storage.user_profiles("printers")
        self.materials = P.materials() + storage.user_profiles("materials")

    def find_printer(self, pid):
        for p in self.printers + ([self.imported_printer] if getattr(self, "imported_printer", None) else []):
            if p and p["id"] == pid:
                return copy.deepcopy(p)
        return None

    def find_material(self, mid):
        for m in self.materials + ([self.imported_material] if getattr(self, "imported_material", None) else []):
            if m and m["id"] == mid:
                return copy.deepcopy(m)
        return None

    def test_params(self, tid):
        prm = G.default_params(tid, self.material, self.printer)
        prm.update(self.params.get(tid, {}))
        return prm

    def save(self):
        storage.save_json(storage.settings_path(), {
            "theme": self.theme, "lang": self.lang, "out_dir": self.out_dir,
            "printer_id": self.printer.get("id"), "material_id": self.material.get("id"),
            "selected": self.selected, "params": self.params})

    def key(self, tid):
        return json.dumps([self.printer, self.material, tid, self.test_params(tid), self.lang], sort_keys=True)


class Generator(QObject):
    """Generates in a background thread; keeps the last results by their inputs."""
    done = Signal(str, object)

    def __init__(self, state):
        super().__init__()
        self.state = state
        self.cache = {}
        self.lock = threading.Lock()
        self.round = 0

    def run_one(self, printer, material, tid, prm, lang):
        key = json.dumps([printer, material, tid, prm, lang], sort_keys=True)
        with self.lock:
            hit = self.cache.get(key)
        if hit is not None:
            return hit
        try:
            res = G.generate(printer, material, tid, prm, lang)
            out = {"ok": True, "res": res, "summary": PR.summary(res), "problems": C.check_result(res, tid),
                   "preview": PV.preview_data(res)}
        except G.DoesNotFit:
            out = {"ok": False, "error": "does_not_fit"}
        except Exception as ex:  # a bad profile must not crash the window
            out = {"ok": False, "error": str(ex)}
        with self.lock:
            if len(self.cache) > 40:
                self.cache.clear()
            self.cache[key] = out
        return out

    def start(self, tids):
        self.round += 1
        rnd = self.round
        s = self.state
        jobs = [(copy.deepcopy(s.printer), copy.deepcopy(s.material), t, s.test_params(t), s.lang) for t in tids]

        def work():
            for printer, material, tid, prm, lang in jobs:
                if rnd != self.round:
                    return
                out = self.run_one(printer, material, tid, prm, lang)
                if rnd == self.round:
                    self.done.emit(tid, out)

        th = threading.Thread(target=work, daemon=True)
        th.start()
        return th

    def now(self, tid):
        s = self.state
        return self.run_one(copy.deepcopy(s.printer), copy.deepcopy(s.material), tid, s.test_params(tid), s.lang)


# ---------------------------------------------------------------- fields

class FieldBinder:
    """Widgets bound to paths in a dict; on change the dict is updated and on_change runs."""

    def __init__(self, get_target, on_change):
        self.get_target = get_target
        self.on_change = on_change
        self.widgets = {}
        self.loading = False

    def num(self, path, decimals=2, lo=0.0, hi=100000.0, step=1.0, integer=False):
        w = QSpinBox() if integer else QDoubleSpinBox()
        w.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        w.setRange(int(lo) if integer else lo, int(hi) if integer else hi)
        if not integer:
            w.setDecimals(decimals)
            w.setSingleStep(step)
        w.setKeyboardTracking(False)
        w.setLocale(QLocale.c())          # a dot, as in G-code, whatever the system language
        w.valueChanged.connect(lambda v, p=path: self._set(p, int(v) if integer else float(v)))
        self.widgets[path] = w
        return w

    def text(self, path):
        w = QLineEdit()
        w.editingFinished.connect(lambda p=path, w=w: self._set(p, w.text()))
        self.widgets[path] = w
        return w

    def choice(self, path, items):
        w = Combo()
        for value, label in items:
            w.addItem(label, value)
        w.currentIndexChanged.connect(lambda i, p=path, w=w: self._set(p, w.itemData(i)))
        self.widgets[path] = w
        return w

    def flag(self, path, label):
        w = QCheckBox(label)
        w.toggled.connect(lambda v, p=path: self._set(p, bool(v)))
        self.widgets[path] = w
        return w

    def code(self, path):
        w = QPlainTextEdit()
        w.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        w.textChanged.connect(lambda p=path, w=w: self._set(p, w.toPlainText().split("\n")))
        self.widgets[path] = w
        return w

    def _set(self, path, value):
        if self.loading:
            return
        set_path(self.get_target(), path, value)
        self.on_change(path)

    def load(self):
        self.loading = True
        try:
            d = self.get_target()
            for path, w in self.widgets.items():
                try:
                    v = get_path(d, path)
                except (KeyError, TypeError):
                    v = None
                if isinstance(w, (QSpinBox, QDoubleSpinBox)):
                    w.setValue(v if isinstance(v, (int, float)) and not isinstance(v, bool) else 0)
                elif isinstance(w, QLineEdit):
                    w.setText("" if v is None else str(v))
                elif isinstance(w, Combo):
                    i = w.findData(v)
                    w.setCurrentIndex(max(0, i))
                elif isinstance(w, QCheckBox):
                    w.setChecked(bool(v))
                elif isinstance(w, QPlainTextEdit):
                    w.setPlainText("\n".join(v or []))
        finally:
            self.loading = False


def form_grid(rows, columns=2):
    """rows: [(label, widget)] laid out in label/field pairs, `columns` pairs per row."""
    g = QGridLayout()
    g.setHorizontalSpacing(12)
    g.setVerticalSpacing(8)
    for i, (label, w) in enumerate(rows):
        r, c = divmod(i, columns)
        lab = QLabel(label)
        lab.setObjectName("muted")
        g.addWidget(lab, r, c * 2)
        g.addWidget(w, r, c * 2 + 1)
    for c in range(columns):
        g.setColumnStretch(c * 2 + 1, 1)
    return g


# ---------------------------------------------------------------- pages

class PrinterPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win, self.s = win, win.state
        L = self.s.lang
        self.setObjectName("page")
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(12)

        imp, il = card("importCard")
        row = QHBoxLayout()
        col = QVBoxLayout()
        t = QLabel(tr("import_title", L))
        t.setObjectName("section")
        col.addWidget(t)
        col.addWidget(wrap_label(tr("import_hint", L), "muted"))
        row.addLayout(col, 1)
        self.import_btn = QPushButton(tr("import_button", L))
        self.import_btn.setObjectName("big")
        self.import_btn.clicked.connect(self.choose_gcode)
        row.addWidget(self.import_btn, 0, Qt.AlignmentFlag.AlignVCenter)
        il.addLayout(row)
        self.report = wrap_label("", "hint")
        self.report.setVisible(False)
        il.addWidget(self.report)
        lay.addWidget(imp)

        prof, pl = card()
        row = QHBoxLayout()
        lab = QLabel(tr("profile", L))
        lab.setObjectName("section")
        row.addWidget(lab)
        self.combo = Combo()
        self.combo.setMinimumWidth(280)
        self.combo.currentIndexChanged.connect(self.pick)
        row.addWidget(self.combo, 1)
        self.badge = QLabel()
        row.addWidget(self.badge)
        pl.addLayout(row)
        self.warning = wrap_label("", "hint")
        pl.addWidget(self.warning)
        btns = QHBoxLayout()
        for key, fn in (("save_profile", self.save_mine), ("delete_profile", self.delete_mine),
                        ("export_json", self.export_json), ("import_json", self.import_json)):
            b = QPushButton(tr(key, L))
            b.clicked.connect(fn)
            btns.addWidget(b)
            setattr(self, "btn_" + key, b)
        btns.addStretch(1)
        pl.addLayout(btns)
        self.status = wrap_label("", "hint")
        pl.addWidget(self.status)
        lay.addWidget(prof)

        f = FieldBinder(lambda: self.s.printer, self.edited)
        self.fields = f
        mech, ml = card()
        h = QLabel(tr("section_bed", L))
        h.setObjectName("section")
        ml.addWidget(h)
        nozzle = f.num("nozzle", 2, 0.1, 1.2, 0.05)
        rows = [
            (tr("name", L), f.text("name")), (tr("prefix", L), f.text("prefix")),
            (tr("bed_x", L), f.num("bed.x", 1, 50, 1000)), (tr("bed_y", L), f.num("bed.y", 1, 50, 1000)),
            (tr("bed_z", L), f.num("bed.z", 1, 50, 1000)),
            (tr("origin", L), f.choice("bed.origin", [("corner", tr("origin_corner", L)), ("center", tr("origin_center", L))])),
            (tr("shape", L), f.choice("bed.shape", [("rect", tr("shape_rect", L)), ("round", tr("shape_round", L))])),
            (tr("nozzle", L), nozzle),
            (tr("filament", L), f.choice("filament_diameter", [(1.75, "1.75"), (2.85, "2.85")])),
            (tr("firmware", L), f.choice("firmware", [("klipper", "Klipper"), ("marlin", "Marlin"), ("rrf", "RepRapFirmware")])),
            (tr("max_speed", L), f.num("max_speed", 0, 20, 2000)), (tr("max_accel", L), f.num("max_accel", 0, 100, 100000, integer=True)),
            (tr("default_accel", L), f.num("default_accel", 0, 100, 100000, integer=True)),
            (tr("travel_speed", L), f.num("travel_speed", 0, 20, 2000)), (tr("z_speed", L), f.num("z_speed", 0, 1, 500)),
            (tr("retract_length", L), f.num("retract.length", 2, 0, 15, 0.1)),
            (tr("retract_speed", L), f.num("retract.speed", 0, 5, 150)), (tr("z_hop", L), f.num("retract.z_hop", 2, 0, 5, 0.1)),
        ]
        ml.addLayout(form_grid(rows, 2))
        opts = QHBoxLayout()
        self.opt_canvas = f.flag("options.canvas", tr("opt_canvas", L))
        self.opt_wipe = f.flag("options.nozzle_wipe", tr("opt_nozzle_wipe", L))
        opts.addWidget(self.opt_canvas)
        opts.addWidget(self.opt_wipe)
        opts.addStretch(1)
        ml.addLayout(opts)
        lay.addWidget(mech)

        code, cl = card()
        h = QLabel(tr("section_code", L))
        h.setObjectName("section")
        cl.addWidget(h)
        cl.addWidget(wrap_label(tr("placeholders_hint", L), "hint"))
        g = QGridLayout()
        for i, (key, path) in enumerate((("start_code", "start_gcode"), ("end_code", "end_gcode"))):
            lab = QLabel(tr(key, L))
            lab.setObjectName("muted")
            g.addWidget(lab, 0, i)
            ed = f.code(path)
            ed.setMinimumHeight(240)
            g.addWidget(ed, 1, i)
        cl.addLayout(g)
        lay.addWidget(code)
        lay.addStretch(1)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll(body))
        self.fill_combo()
        self.show_printer()

    def fill_combo(self):
        L = self.s.lang
        self.combo.blockSignals(True)
        self.combo.clear()
        items = list(self.s.printers)
        if self.s.imported_printer:
            items.append(self.s.imported_printer)
        for p in items:
            mark = "✓ " if p.get("verified") else ""
            mine = f"  ({tr('my_profile', L)})" if p.get("_user") else ""
            self.combo.addItem(mark + p["name"] + mine, p["id"])
        i = self.combo.findData(self.s.printer.get("id"))
        self.combo.setCurrentIndex(max(0, i))
        self.combo.blockSignals(False)

    def pick(self, i):
        pid = self.combo.itemData(i)
        p = self.s.find_printer(pid)
        if p:
            self.s.printer = p
            self.show_printer()
            self.s.changed.emit("printer")

    def show_printer(self):
        L = self.s.lang
        p = self.s.printer
        self.fields.load()
        self.opt_canvas.setVisible("canvas" in (p.get("options") or {}))
        self.opt_wipe.setVisible("nozzle_wipe" in (p.get("options") or {}))
        if p.get("verified"):
            self.badge.setText("✓ " + tr("verified", L))
            self.badge.setObjectName("badgeOk")
        else:
            self.badge.setText("⚠ " + tr("unverified", L))
            self.badge.setObjectName("badgeWarn")
        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)
        parts = []
        if not p.get("verified"):
            parts.append(tr("unverified_hint", L))
        if p.get("warning") and p.get("id", "").startswith("bambu"):
            parts.append(tr("import_bambu", L))
        if p.get("source"):
            parts.append(tr("source", L) + ": " + p["source"])
        self.warning.setText("\n".join(parts))
        self.btn_delete_profile.setEnabled(bool(p.get("_user")))
        self.mark_missing(self.s.import_report["missing"] if self.s.import_report and p.get("id") == "imported" else [])
        self.validate()

    def mark_missing(self, missing):
        for path, w in self.fields.widgets.items():
            w.setProperty("missing", path in missing)
            w.style().unpolish(w)
            w.style().polish(w)

    def validate(self):
        errs = P.validate_printer({k: v for k, v in self.s.printer.items() if not k.startswith("_")})
        if errs:
            self.status.setObjectName("error")
            self.status.setText(tr("profile_errors", self.s.lang, errors="; ".join(errs[:4])))
        else:
            self.status.setObjectName("hint")
            self.status.setText("")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        return errs

    def edited(self, path):
        w = self.fields.widgets.get(path)
        if w is not None and w.property("missing"):
            w.setProperty("missing", False)
            w.style().unpolish(w)
            w.style().polish(w)
        self.validate()
        self.s.changed.emit("printer")

    # import
    def choose_gcode(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("import_title", self.s.lang), self.s.out_dir,
                                              "G-code (*.gcode *.gco *.g);;* (*)")
        if path:
            self.import_file(path)

    def import_file(self, path):
        L = self.s.lang
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
            r = I.parse(text, Path(path).name)
        except OSError as ex:
            self.report.setText(tr("import_failed", L, error=ex))
            self.report.setVisible(True)
            return None
        fw = r["printer"].get("firmware") or self.s.printer.get("firmware", "marlin")
        base = P.printer(BASES.get(fw, "generic-marlin"))
        mtype = (r["material"].get("type") or "").lower()
        base_mat = self.s.find_material(mtype) or copy.deepcopy(self.s.material)
        printer, material = I.to_profiles(r, base, base_mat)
        self.s.imported_printer = copy.deepcopy(printer)
        self.s.imported_material = copy.deepcopy(material)
        self.s.import_report = r
        self.s.printer = printer
        self.s.material = material
        lines = [tr("import_done", L, file=r["file"], slicer=r["slicer"] or "?")]
        lines.append(tr("import_replaced", L, n=len(r["replaced"])))
        for rep in r["replaced"][:8]:
            lines.append(f"   {rep['before']}  →  {rep['after']}")
        lines.append(tr("import_missing", L, fields=", ".join(r["missing"])) if r["missing"] else tr("import_all_found", L))
        if "bambu" in r["warnings"]:
            lines.append(tr("import_bambu", L))
        if "firmware_unknown" in r["warnings"]:
            lines.append(tr("import_fw_unknown", L))
        self.report.setText("\n".join(lines))
        self.report.setVisible(True)
        self.fill_combo()
        self.show_printer()
        self.s.changed.emit("printer")
        self.s.changed.emit("material")
        return r

    # profiles
    def save_mine(self):
        if self.validate():
            return
        pid = storage.save_user_profile("printers", self.s.printer)
        if pid:
            self.s.reload_profiles()
            self.s.printer = self.s.find_printer(pid)
            self.fill_combo()
            self.show_printer()
            self.status.setText(tr("saved", self.s.lang, name=self.s.printer["name"]))

    def delete_mine(self):
        if self.s.printer.get("_user") and storage.delete_user_profile("printers", self.s.printer["id"]):
            self.s.reload_profiles()
            self.s.printer = self.s.find_printer("elegoo-centauri-carbon")
            self.fill_combo()
            self.show_printer()
            self.s.changed.emit("printer")

    def export_json(self, path=None):
        if not path:
            path, _ = QFileDialog.getSaveFileName(self, tr("export_json", self.s.lang),
                                                  str(Path(self.s.out_dir) / (storage.slug(self.s.printer["name"]) + ".json")), "JSON (*.json)")
        if path:
            storage.save_json(path, {k: v for k, v in self.s.printer.items() if not k.startswith("_")})
        return path

    def import_json(self, path=None):
        if not path:
            path, _ = QFileDialog.getOpenFileName(self, tr("import_json", self.s.lang), self.s.out_dir, "JSON (*.json)")
        if not path:
            return None
        data = storage.load_json(path)
        errs = P.validate_printer(data) if isinstance(data, dict) else ["not a profile"]
        if errs:
            self.status.setObjectName("error")
            self.status.setText(tr("profile_errors", self.s.lang, errors="; ".join(errs[:4])))
            return errs
        pid = storage.save_user_profile("printers", data)
        self.s.reload_profiles()
        self.s.printer = self.s.find_printer(pid)
        self.fill_combo()
        self.show_printer()
        self.s.changed.emit("printer")
        return []


class MaterialPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win, self.s = win, win.state
        L = self.s.lang
        self.setObjectName("page")
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(12)
        top, tl = card()
        row = QHBoxLayout()
        lab = QLabel(tr("material", L))
        lab.setObjectName("section")
        row.addWidget(lab)
        self.combo = Combo()
        self.combo.setMinimumWidth(220)
        self.combo.currentIndexChanged.connect(self.pick)
        row.addWidget(self.combo, 1)
        self.badge = QLabel()
        row.addWidget(self.badge)
        tl.addLayout(row)
        btns = QHBoxLayout()
        b = QPushButton(tr("save_profile", L))
        b.clicked.connect(self.save_mine)
        btns.addWidget(b)
        btns.addStretch(1)
        tl.addLayout(btns)
        self.status = wrap_label("", "hint")
        tl.addWidget(self.status)
        lay.addWidget(top)

        f = FieldBinder(lambda: self.s.material, self.edited)
        self.fields = f
        form, fl = card()
        rows = [
            (tr("name", L), f.text("name")), (tr("mat_type", L), f.text("type")),
            (tr("nozzle_temp", L), f.num("nozzle_temp", 0, 150, 350, integer=True)),
            (tr("first_layer_temp", L), f.num("first_layer_temp", 0, 150, 350, integer=True)),
            (tr("bed_temp", L), f.num("bed", 0, 0, 130, integer=True)),
            (tr("tower_start", L), f.num("tower.start", 0, 150, 350, integer=True)),
            (tr("tower_end", L), f.num("tower.end", 0, 150, 350, integer=True)),
            (tr("tower_step", L), f.num("tower.step", 0, 1, 20, integer=True)),
            (tr("flow", L), f.num("flow", 3, 0.5, 1.5, 0.01)), (tr("mvs", L), f.num("mvs", 1, 0.5, 60, 0.5)),
            (tr("fan", L), f.num("fan", 2, 0, 1, 0.05)), (tr("bridge_fan", L), f.num("bridge_fan", 2, 0, 1, 0.05)),
            (tr("fan_off_layers", L), f.num("fan_off_layers", 0, 0, 10, integer=True)),
            (tr("min_layer_time", L), f.num("min_layer_time", 1, 0, 60, 0.5)),
            (tr("pa_default", L), f.num("pa_default", 3, 0, 2, 0.001)), (tr("density", L), f.num("density", 2, 0.8, 2.0, 0.01)),
            (tr("max_flow_from", L), f.num("max_flow.0", 1, 0.5, 80, 0.5)), (tr("max_flow_to", L), f.num("max_flow.1", 1, 0.5, 80, 0.5)),
        ]
        fl.addLayout(form_grid(rows, 2))
        lay.addWidget(form)
        lay.addStretch(1)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll(body))
        self.fill_combo()
        self.show_material()

    def fill_combo(self):
        L = self.s.lang
        self.combo.blockSignals(True)
        self.combo.clear()
        items = list(self.s.materials) + ([self.s.imported_material] if self.s.imported_material else [])
        for m in items:
            mine = f"  ({tr('my_profile', L)})" if m.get("_user") else ""
            self.combo.addItem(("✓ " if m.get("verified") else "") + m["name"] + mine, m["id"])
        self.combo.setCurrentIndex(max(0, self.combo.findData(self.s.material.get("id"))))
        self.combo.blockSignals(False)

    def pick(self, i):
        m = self.s.find_material(self.combo.itemData(i))
        if m:
            self.s.material = m
            self.show_material()
            self.s.changed.emit("material")

    def show_material(self):
        L = self.s.lang
        m = self.s.material
        self.fields.load()
        self.badge.setText(("✓ " + tr("mat_verified", L)) if m.get("verified") else tr("mat_generic", L))
        self.badge.setObjectName("badgeOk" if m.get("verified") else "muted")
        self.badge.style().unpolish(self.badge)
        self.badge.style().polish(self.badge)
        self.validate()

    def validate(self):
        errs = P.validate_material({k: v for k, v in self.s.material.items() if not k.startswith("_")})
        self.status.setObjectName("error" if errs else "hint")
        self.status.setText(tr("profile_errors", self.s.lang, errors="; ".join(errs[:4])) if errs else "")
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)
        return errs

    def edited(self, path):
        self.validate()
        self.s.changed.emit("material")

    def save_mine(self):
        if self.validate():
            return
        mid = storage.save_user_profile("materials", self.s.material)
        if mid:
            self.s.reload_profiles()
            self.s.material = self.s.find_material(mid)
            self.fill_combo()
            self.show_material()
            self.status.setText(tr("saved", self.s.lang, name=self.s.material["name"]))


class TestsPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win, self.s = win, win.state
        L = self.s.lang
        self.setObjectName("page")
        self.results = {}
        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(12)
        left = QVBoxLayout()
        left.addWidget(wrap_label(tr("tests_hint", L), "muted"))
        self.list = QListWidget()
        self.list.setMinimumWidth(300)
        for t in PR.tests():
            it = QListWidgetItem(t["name"][L])
            it.setData(Qt.ItemDataRole.UserRole, t["id"])
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked if t["id"] in self.s.selected else Qt.CheckState.Unchecked)
            self.list.addItem(it)
        self.list.itemChanged.connect(self.checked)
        self.list.currentRowChanged.connect(self.show_test)
        left.addWidget(self.list, 1)
        row = QHBoxLayout()
        for key, on in (("select_all", True), ("select_none", False)):
            b = QPushButton(tr(key, L))
            b.clicked.connect(lambda _=False, on=on: self.select_all(on))
            row.addWidget(b)
        row.addStretch(1)
        left.addLayout(row)
        self.total = wrap_label("", "hint")
        left.addWidget(self.total)
        lay.addLayout(left, 0)

        self.detail = QWidget()
        dl = QVBoxLayout(self.detail)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(10)
        head, hl = card()
        self.title = QLabel()
        self.title.setObjectName("title")
        hl.addWidget(self.title)
        self.look = wrap_label()
        hl.addWidget(self.look)
        self.where = wrap_label("", "muted")
        hl.addWidget(self.where)
        self.fast = wrap_label(tr("fast_warning", L), "error")
        hl.addWidget(self.fast)
        dl.addWidget(head)
        self.params_card, self.params_lay = card()
        dl.addWidget(self.params_card)
        prev, pv = card()
        self.info = wrap_label("", "big")
        pv.addWidget(self.info)
        self.check_label = wrap_label("", "hint")
        pv.addWidget(self.check_label)
        views = QHBoxLayout()
        self.views, self.view_boxes = {}, {}
        for mode, key in (("top", "preview_top"), ("front", "preview_front")):
            box = QWidget()
            col = QVBoxLayout(box)
            col.setContentsMargins(0, 0, 0, 0)
            lab = QLabel(tr(key, L))
            lab.setObjectName("muted")
            col.addWidget(lab)
            v = PreviewView(mode)
            col.addWidget(v, 1)
            self.views[mode] = v
            self.view_boxes[mode] = box
            views.addWidget(box, 1)
        pv.addLayout(views, 1)
        dl.addWidget(prev, 1)
        lay.addWidget(scroll(self.detail), 1)
        self.param_widgets = {}
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(250)
        self.timer.timeout.connect(self.recompute)
        win.gen.done.connect(self.got)
        self.list.setCurrentRow(0)
        self.recompute()

    def colors(self, pal):
        for v in self.views.values():
            v.set_colors(pal["canvas"], "#3a3f4b" if pal["dark"] or True else "#c9ced8")

    def current(self):
        it = self.list.currentItem()
        return it.data(Qt.ItemDataRole.UserRole) if it else G.TEST_IDS[0]

    def checked(self, it):
        tid = it.data(Qt.ItemDataRole.UserRole)
        on = it.checkState() == Qt.CheckState.Checked
        if on == (tid in self.s.selected):
            return          # only the text changed
        sel = [t for t in G.TEST_IDS if (t in self.s.selected and t != tid) or (t == tid and on)]
        self.s.selected = sel
        self.update_total()
        self.s.changed.emit("selected")

    def select_all(self, on):
        self.list.blockSignals(True)
        for i in range(self.list.count()):
            self.list.item(i).setCheckState(Qt.CheckState.Checked if on else Qt.CheckState.Unchecked)
        self.list.blockSignals(False)
        self.s.selected = list(G.TEST_IDS) if on else []
        self.update_total()
        self.s.changed.emit("selected")

    def schedule(self):
        self.timer.start()

    def recompute(self):
        self.results = {}
        for i in range(self.list.count()):
            it = self.list.item(i)
            tid = it.data(Qt.ItemDataRole.UserRole)
            it.setText(PR.test_info(tid)["name"][self.s.lang] + "   …")
        self.info.setText(tr("computing", self.s.lang))
        cur = self.current()
        order = [cur] + [t for t in G.TEST_IDS if t != cur]
        self.win.gen.start(order)

    def got(self, tid, out):
        self.results[tid] = out
        L = self.s.lang
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.data(Qt.ItemDataRole.UserRole) == tid:
                name = PR.test_info(tid)["name"][L]
                if out["ok"]:
                    sm = out["summary"]
                    warn = "  ⚠" if out["problems"] else ""
                    it.setText(f"{name}   {fmt_time(sm['minutes'], L)} · {sm['grams']} {tr('grams', L)}{warn}")
                else:
                    it.setText(f"{name}   ⚠")
        if tid == self.current():
            self.show_result(tid)
        self.update_total()
        self.win.download.refresh()

    def update_total(self):
        L = self.s.lang
        mins, grams, n = 0, 0.0, 0
        for t in self.s.selected:
            out = self.results.get(t)
            if out and out["ok"]:
                mins += out["summary"]["minutes"]
                grams += float(out["summary"]["grams"])
                n += 1
        self.total.setText(tr("total", L, n=len(self.s.selected), time=fmt_time(mins, L), grams=f"{grams:.0f}"))

    def show_test(self, row):
        if row < 0:
            return
        L = self.s.lang
        tid = self.current()
        info = PR.test_info(tid)
        self.title.setText(info["name"][L])
        self.look.setText(tr("look_for", L) + ": " + info["look"][L])
        self.where.setText(tr("result_where", L) + ": " + info["result"][L])
        self.fast.setVisible(bool(info.get("fast")))
        self.build_params(tid)
        self.show_result(tid)

    def build_params(self, tid):
        while self.params_lay.count():
            item = self.params_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                lay = item.layout()
                while lay.count():
                    sub = lay.takeAt(0)
                    if sub.widget():
                        sub.widget().deleteLater()
        L = self.s.lang
        info = PR.test_info(tid)
        self.params_card.setVisible(bool(info["params"]))
        if not info["params"]:
            return
        lab = QLabel(tr("params", L))
        lab.setObjectName("section")
        self.params_lay.addWidget(lab)
        prm = self.s.test_params(tid)
        holder = QWidget()
        g = QGridLayout(holder)
        g.setContentsMargins(0, 0, 0, 0)
        self.param_widgets = {}
        for i, spec in enumerate(info["params"]):
            key = spec["key"]
            lab = QLabel(spec["label"][L])
            lab.setObjectName("muted")
            if spec["type"] == "list":
                w = QLineEdit(" ".join(f"{v:.{spec.get('digits', 2)}f}" for v in prm[key]))
                w.editingFinished.connect(lambda tid=tid, key=key, w=w: self.param_list(tid, key, w))
            elif spec["type"] == "int":
                w = QSpinBox()
                w.setRange(int(spec["min"]), int(spec["max"]))
                w.setSingleStep(int(spec["step"]))
                w.setValue(int(prm[key]))
            else:
                w = QDoubleSpinBox()
                w.setDecimals(spec.get("digits", 2))
                w.setRange(spec["min"], spec["max"])
                w.setSingleStep(spec["step"])
                w.setValue(float(prm[key]))
            if isinstance(w, (QSpinBox, QDoubleSpinBox)):
                w.setLocale(QLocale.c())
                w.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
                w.setKeyboardTracking(False)
                w.valueChanged.connect(lambda v, tid=tid, key=key, spec=spec: self.param_num(tid, key, spec, v))
            self.param_widgets[key] = w
            r, c = divmod(i, 3)
            g.addWidget(lab, r * 2, c)
            g.addWidget(w, r * 2 + 1, c)
        self.params_lay.addWidget(holder)
        self.param_err = wrap_label("", "error")
        self.params_lay.addWidget(self.param_err)
        self.check_params(tid)

    def param_num(self, tid, key, spec, v):
        v = int(v) if spec["type"] == "int" else round(float(v), spec.get("digits", 3))
        self.s.params.setdefault(tid, {})[key] = v
        if self.check_params(tid):
            self.s.changed.emit("params")

    def param_list(self, tid, key, w):
        try:
            vals = [round(float(x.replace(",", ".")), 3) for x in w.text().split()]
        except ValueError:
            vals = []
        self.s.params.setdefault(tid, {})[key] = vals
        if self.check_params(tid):
            self.s.changed.emit("params")

    def check_params(self, tid):
        errs = PR.validate(tid, self.s.test_params(tid), self.s.printer, self.s.material)
        if hasattr(self, "param_err"):
            self.param_err.setText("; ".join(errs))
            self.param_err.setVisible(bool(errs))
        return not errs

    def show_result(self, tid):
        L = self.s.lang
        out = self.results.get(tid)
        if out is None:
            self.info.setText(tr("computing", L))
            self.check_label.setText("")
            for v in self.views.values():
                v.set_data(None)
            return
        if not out["ok"]:
            err = tr("does_not_fit", L) if out["error"] == "does_not_fit" else out["error"]
            self.info.setText(tr("gen_error", L, error=err))
            self.check_label.setText("")
            for v in self.views.values():
                v.set_data(None)
            return
        sm = out["summary"]
        self.info.setText(f"{sm['name']}\n{tr('time_grams', L, time=fmt_time(sm['minutes'], L), grams=sm['grams'])}")
        if out["problems"]:
            self.check_label.setObjectName("error")
            self.check_label.setText(tr("check_failed", L, problems="; ".join(out["problems"][:3])))
        else:
            self.check_label.setObjectName("ok")
            self.check_label.setText("✓ " + tr("check_ok", L))
        self.check_label.style().unpolish(self.check_label)
        self.check_label.style().polish(self.check_label)
        for v in self.views.values():
            v.set_data(out["preview"])
        self.view_boxes["front"].setVisible(out["preview"]["front"] is not None)


class DownloadPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win, self.s = win, win.state
        L = self.s.lang
        self.setObjectName("page")
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(12)
        top, tl = card()
        tl.addWidget(wrap_label(tr("download_hint", L), "muted"))
        row = QHBoxLayout()
        self.btn_folder = QPushButton(tr("save_folder", L))
        self.btn_folder.setObjectName("primary")
        self.btn_folder.clicked.connect(self.choose_folder)
        self.btn_zip = QPushButton(tr("save_zip", L))
        self.btn_zip.clicked.connect(self.choose_zip)
        row.addWidget(self.btn_folder)
        row.addWidget(self.btn_zip)
        row.addStretch(1)
        tl.addLayout(row)
        self.status = wrap_label("", "ok")
        tl.addWidget(self.status)
        tl.addWidget(wrap_label(tr("watch_first", L), "hint"))
        lay.addWidget(top)
        order, ol = card()
        lab = QLabel(tr("print_order", L))
        lab.setObjectName("section")
        ol.addWidget(lab)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([tr(k, L) for k in ("col_n", "col_file", "col_time", "col_look", "col_result")])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(True)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumHeight(360)
        ol.addWidget(self.table, 1)
        self.total = wrap_label("", "hint")
        ol.addWidget(self.total)
        lay.addWidget(order, 1)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll(body))
        self.refresh()

    def refresh(self):
        L = self.s.lang
        res = self.win.tests.results if hasattr(self.win, "tests") else {}
        sel = self.s.selected
        self.table.setRowCount(len(sel))
        mins, grams = 0, 0.0
        for r, tid in enumerate(sel):
            info = PR.test_info(tid)
            out = res.get(tid)
            name = out["summary"]["name"] if out and out["ok"] else info["name"][L]
            time = fmt_time(out["summary"]["minutes"], L) if out and out["ok"] else "…"
            if out and out["ok"]:
                mins += out["summary"]["minutes"]
                grams += float(out["summary"]["grams"])
            for c, text in enumerate((str(r + 1), name, time, info["look"][L], info["result"][L])):
                it = QTableWidgetItem(text)
                self.table.setItem(r, c, it)
        self.table.resizeRowsToContents()
        self.total.setText(tr("total", L, n=len(sel), time=fmt_time(mins, L), grams=f"{grams:.0f}"))
        self.btn_folder.setEnabled(bool(sel))
        self.btn_zip.setEnabled(bool(sel))

    def files(self):
        out = []
        for tid in self.s.selected:
            r = self.win.gen.now(tid)
            if r["ok"]:
                out.append((r["summary"]["name"], r["res"].text))
        return out

    def choose_folder(self):
        path = QFileDialog.getExistingDirectory(self, tr("save_folder", self.s.lang), self.s.out_dir)
        if path:
            self.save_folder(path)

    def save_folder(self, path):
        files = self.files()
        for name, text in files:
            (Path(path) / name).write_text(text, encoding="utf-8", newline="\n")
        self.s.out_dir = str(path)
        self.status.setText(tr("saved_files", self.s.lang, n=len(files), path=path))
        return [name for name, _ in files]

    def choose_zip(self):
        name = f"{self.s.printer.get('prefix', 'calib')}_{self.s.material.get('type', '')}_calibration.zip"
        path, _ = QFileDialog.getSaveFileName(self, tr("save_zip", self.s.lang), str(Path(self.s.out_dir) / name), "ZIP (*.zip)")
        if path:
            self.save_zip(path)

    def save_zip(self, path):
        files = self.files()
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            for name, text in files:
                z.writestr(name, text.encode("utf-8"))
        self.s.out_dir = str(Path(path).parent)
        self.status.setText(tr("saved_files", self.s.lang, n=len(files), path=path))
        return [name for name, _ in files]


class ResultsPage(QWidget):
    def __init__(self, win):
        super().__init__()
        self.win, self.s = win, win.state
        L = self.s.lang
        self.setObjectName("page")
        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(10)
        lay.addWidget(wrap_label(tr("results_hint", L), "muted"))
        self.inputs, self.outputs = {}, {}
        for i, t in enumerate(PR.tests()):
            c, cl = card()
            h = QLabel(f"{i + 1}. {t['name'][L]}")
            h.setObjectName("section")
            cl.addWidget(h)
            cl.addWidget(wrap_label(t["look"][L]))
            if t["helper"]:
                row = QHBoxLayout()
                lab = QLabel(t["helper"]["input"][L])
                lab.setObjectName("muted")
                row.addWidget(lab)
                e = QLineEdit()
                e.setMaximumWidth(220)
                e.textChanged.connect(lambda _t, tid=t["id"]: self.compute(tid))
                row.addWidget(e)
                row.addStretch(1)
                cl.addLayout(row)
                out = wrap_label("", "big")
                cl.addWidget(out)
                self.inputs[t["id"]], self.outputs[t["id"]] = e, out
            else:
                cl.addWidget(wrap_label(t["result"][L], "muted"))
            lay.addWidget(c)
        lay.addStretch(1)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll(body))

    def compute(self, tid):
        L = self.s.lang
        text = self.inputs[tid].text()
        if not text.strip():
            self.outputs[tid].setText("")
            return
        r = PR.helper(tid, text, self.s.printer, self.s.material, self.s.test_params(tid))
        self.outputs[tid].setText(tr(r["note"], L, value=r["value"]) if r["ok"] else tr(r["error"], L))


# ---------------------------------------------------------------- window

class MainWindow(QMainWindow):
    def __init__(self, remember=True):
        super().__init__()
        self.state = State()
        self.gen = Generator(self.state)
        self.state.changed.connect(self.on_changed)
        self.setWindowTitle(tr("app_title", self.state.lang))
        self.setMinimumSize(WINDOW_OPTS["minWidth"], WINDOW_OPTS["minHeight"])
        self.memory = WindowMemory(self, storage.window_path(), WINDOW_OPTS) if remember else None
        if not remember:
            self.resize(WINDOW_OPTS["width"], WINDOW_OPTS["height"])
        self.build()
        self.apply_theme()

    def build(self, index=0):
        L = self.state.lang
        self.setWindowTitle(tr("app_title", L))
        root = QWidget()
        root.setObjectName("root")
        lay = QVBoxLayout(root)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(8)
        head = QHBoxLayout()
        col = QVBoxLayout()
        t = QLabel(tr("app_title", L))
        t.setObjectName("title")
        col.addWidget(t)
        sub = QLabel(tr("app_sub", L) + "  ·  " + tr("version", L, v=P.version()))
        sub.setObjectName("subtitle")
        col.addWidget(sub)
        head.addLayout(col, 1)
        lab = QLabel(tr("theme", L))
        lab.setObjectName("muted")
        head.addWidget(lab)
        self.theme_combo = Combo()
        for th in theme.THEMES:
            self.theme_combo.addItem(tr("theme_" + th, L), th)
        self.theme_combo.setCurrentIndex(theme.THEMES.index(self.state.theme))
        self.theme_combo.currentIndexChanged.connect(lambda i: self.set_theme(theme.THEMES[i]))
        head.addWidget(self.theme_combo)
        lab = QLabel(tr("language", L))
        lab.setObjectName("muted")
        head.addWidget(lab)
        self.lang_combo = Combo()
        self.lang_combo.addItem("Русский", "ru")
        self.lang_combo.addItem("English", "en")
        self.lang_combo.setCurrentIndex(0 if L == "ru" else 1)
        self.lang_combo.currentIndexChanged.connect(lambda i: self.set_lang(self.lang_combo.itemData(i)))
        head.addWidget(self.lang_combo)
        lay.addLayout(head)

        bar = QHBoxLayout()
        bar.setSpacing(2)
        self.step_buttons = QButtonGroup(self)
        self.step_buttons.setExclusive(True)
        for i, key in enumerate(STEPS):
            b = QPushButton(tr(key, L))
            b.setObjectName("step")
            b.setCheckable(True)
            b.clicked.connect(lambda _=False, i=i: self.go(i))
            self.step_buttons.addButton(b, i)
            bar.addWidget(b)
            if i == 3:
                bar.addStretch(1)
        lay.addLayout(bar)

        self.stack = QStackedWidget()
        self.printer = PrinterPage(self)
        self.material = MaterialPage(self)
        self.tests = TestsPage(self)
        self.download = DownloadPage(self)
        self.results = ResultsPage(self)
        for page in (self.printer, self.material, self.tests, self.download, self.results):
            self.stack.addWidget(page)
        lay.addWidget(self.stack, 1)

        nav = QHBoxLayout()
        self.back_btn = QPushButton(tr("back", L))
        self.back_btn.clicked.connect(lambda: self.go(self.stack.currentIndex() - 1))
        self.next_btn = QPushButton(tr("next", L))
        self.next_btn.setObjectName("primary")
        self.next_btn.clicked.connect(lambda: self.go(self.stack.currentIndex() + 1))
        nav.addWidget(self.back_btn)
        nav.addStretch(1)
        nav.addWidget(self.next_btn)
        lay.addLayout(nav)
        old = self.centralWidget()
        self.setCentralWidget(root)
        if old is not None:
            old.deleteLater()
        self.go(index)

    def go(self, i):
        i = max(0, min(len(STEPS) - 1, i))
        self.stack.setCurrentIndex(i)
        self.step_buttons.button(i).setChecked(True)
        self.back_btn.setEnabled(i > 0)
        self.next_btn.setVisible(i < 3)
        if i == 3:
            self.download.refresh()

    def on_changed(self, what):
        self.state.save()
        if not hasattr(self, "download"):
            return          # still building the pages
        if what in ("printer", "material", "params"):
            self.tests.schedule()
            if what == "material":
                self.material.fill_combo()
                self.material.show_material()
                self.tests.build_params(self.tests.current())
        if what == "selected":
            self.download.refresh()

    def set_theme(self, name):
        self.state.theme = name
        self.state.save()
        self.apply_theme()

    def apply_theme(self):
        pal = theme.palette(self.state.theme)
        Combo.arrow_color = pal["muted"]
        app = QApplication.instance()
        app.setStyleSheet(theme.qss(self.state.theme))
        self.tests.colors(pal)
        for w in self.findChildren(Combo):
            w.update()

    def set_lang(self, lang):
        if lang == self.state.lang:
            return
        self.state.lang = lang
        self.state.save()
        self.build(self.stack.currentIndex())
        self.apply_theme()

    def moveEvent(self, e):
        super().moveEvent(e)
        if self.memory:
            self.memory.track()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        if self.memory:
            self.memory.track()

    def closeEvent(self, e):
        if self.memory:
            self.memory.save()
        self.state.save()
        super().closeEvent(e)

    def show_remembered(self):
        if self.memory:
            self.memory.show()
        else:
            self.show()


def main(argv=None):
    app = QApplication.instance() or QApplication(sys.argv if argv is None else argv)
    app.setApplicationName("Calibrate3dPrinter")
    app.setFont(QFont("Segoe UI", 10))
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
    icon = base / "assets" / "icon.png"
    if icon.exists():
        app.setWindowIcon(QIcon(str(icon)))
    win = MainWindow()
    win.show_remembered()
    return app.exec()
