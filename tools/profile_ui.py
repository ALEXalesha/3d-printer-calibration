"""Where the Qt window stalls: a heartbeat timer on the UI thread records the longest gap
between ticks while the usual actions run, offscreen (no window on the screen).

    python tools/profile_ui.py            # table of actions and their longest stall
    python tools/profile_ui.py --profile  # plus cProfile of the main thread per action

A stall is the longest time the event loop could not run (the window would not repaint
or react to the mouse). tests/py/test_ui_speed.py holds the budget.
"""
import cProfile
import io
import os
import pstats
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
os.environ["CALIB3D_HOME"] = tempfile.mkdtemp(prefix="calib3d-prof-")

from PySide6.QtCore import QElapsedTimer, QTimer  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


class Heartbeat:
    """Ticks every 5 ms on the UI thread; remembers the longest gap."""

    def __init__(self):
        self.clock = QElapsedTimer()
        self.clock.start()
        self.last = 0
        self.worst = 0
        self.timer = QTimer()
        self.timer.setInterval(5)
        self.timer.timeout.connect(self.tick)
        self.timer.start()

    def tick(self):
        now = self.clock.elapsed()
        self.worst = max(self.worst, now - self.last)
        self.last = now

    def reset(self):
        self.last = self.clock.elapsed()
        self.worst = 0


def pump(app, seconds, until=None):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        if until and until():
            break
        time.sleep(0.002)


def actions(win, app):
    """name -> callable that starts the action; the measure runs until it settles."""
    samples = ROOT / "tests" / "import"

    def tower():
        win.go(2)
        win.tests.list.setCurrentRow(1)

    def overhang():
        win.tests.list.setCurrentRow(6)

    def edit_field():
        win.go(0)
        w = win.printer.fields.widgets["retract.length"]
        w.setValue(w.value() + 0.1)

    def type_start_code():
        ed = win.printer.fields.widgets["start_gcode"]
        for ch in "; hello":
            ed.insertPlainText(ch)
            app.processEvents()

    def material():
        win.go(1)
        win.material.combo.setCurrentIndex(0)

    def theme_switch():
        win.theme_combo.setCurrentIndex(2)

    def lang_switch():
        win.lang_combo.setCurrentIndex(1)

    def import_file():
        win.printer.import_file(str(samples / "orca.gcode"))

    def download_page():
        win.go(3)

    def resize():
        win.resize(1000, 700)

    return [("start (generate all)", None), ("show temp tower", tower), ("show overhangs", overhang),
            ("edit a printer field", edit_field), ("type in start code", type_start_code), ("pick a material", material),
            ("switch theme", theme_switch), ("switch language", lang_switch), ("import a G-code", import_file),
            ("open download page", download_page), ("resize window", resize)]


def main():
    profile = "--profile" in sys.argv
    app = QApplication([])
    hb = Heartbeat()
    from calib3d.ui.app import MainWindow
    rows = []
    t0 = time.perf_counter()
    win = MainWindow(remember=False)
    win.resize(1180, 800)
    win.show()
    rows.append(("build window", round((time.perf_counter() - t0) * 1000), hb.worst))
    for name, act in actions(win, app):
        hb.reset()
        prof = cProfile.Profile() if profile else None
        t = time.perf_counter()
        if prof:
            prof.enable()
        if act:
            act()
        pump(app, 30, until=lambda: len(win.tests.results) == 10 and not win.tests.timer.isActive())
        pump(app, 0.3)
        if prof:
            prof.disable()
        rows.append((name, round((time.perf_counter() - t) * 1000), hb.worst))
        if prof:
            s = io.StringIO()
            pstats.Stats(prof, stream=s).sort_stats("cumulative").print_stats(12)
            print(f"===== {name}\n" + s.getvalue()[:2500])
    print(f"{'action':28} {'took ms':>8} {'worst stall ms':>15}")
    for name, took, worst in rows:
        print(f"{name:28} {took:8} {worst:15}")
    win.gen.round += 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
