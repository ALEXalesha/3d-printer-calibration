"""Screenshots of the Qt window, offscreen (no window on the screen).

    python tools/screens_py.py <out dir> [themes] [langs]

Every step in each theme and language: <out>/py_<theme>_<lang>_<n>_<step>.png. The
window is drawn by the program itself (QWidget.grab), never a photo of the screen.
"""
import os
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "python"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ.setdefault("QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts"))
os.environ["CALIB3D_HOME"] = tempfile.mkdtemp(prefix="calib3d-shots-")

from PySide6.QtWidgets import QApplication  # noqa: E402

STEPS = ["printer", "material", "tests", "download", "results"]


def wait(app, cond, timeout=90):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        app.processEvents()
        if cond():
            return True
        time.sleep(0.01)
    return False


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / "local" / "shots")
    themes = sys.argv[2].split(",") if len(sys.argv) > 2 else ["light", "glass"]
    langs = sys.argv[3].split(",") if len(sys.argv) > 3 else ["ru", "en"]
    out.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    from calib3d.ui.app import MainWindow
    win = MainWindow(remember=False)
    win.resize(1180, 800)
    win.show()
    for lang in langs:
        win.set_lang(lang)
        for th in themes:
            win.set_theme(th)
            win.theme_combo.blockSignals(True)
            win.theme_combo.setCurrentIndex(["glass", "formal", "light", "night", "warm"].index(th))
            win.theme_combo.blockSignals(False)
            if not wait(app, lambda: len(win.tests.results) == 10):
                raise SystemExit("generation did not finish")
            for i, step in enumerate(STEPS):
                win.go(i)
                if step == "tests":
                    win.tests.list.setCurrentRow(1)
                if step == "results":
                    win.results.inputs["pressure_advance"].setText("024")
                    win.results.inputs["flow"].setText("104")
                app.processEvents()
                path = out / f"py_{th}_{lang}_{i + 1}_{step}.png"
                win.grab().save(str(path))
                print(path)
    win.gen.round += 1
    win.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
