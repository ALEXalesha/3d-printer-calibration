"""The Qt window, offscreen (QT_QPA_PLATFORM=offscreen): never a visible window."""
import re
import time
import zipfile
from pathlib import Path

import pytest

from calib3d.core import generator as G
from calib3d.core import profiles as P

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "tests" / "import"


def wait(app, cond, timeout=90.0):
    """Process events until cond() or the timeout; never an endless loop."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        app.processEvents()
        if cond():
            return True
        time.sleep(0.01)
    return False


@pytest.fixture
def win(qapp):
    from calib3d.ui.app import MainWindow
    w = MainWindow(remember=False)
    w.resize(1180, 800)
    w.show()
    assert wait(qapp, lambda: len(w.tests.results) == 10), "generation did not finish"
    yield w
    w.gen.round += 1          # stop a running background round
    w.close()
    w.deleteLater()
    qapp.processEvents()


def test_offscreen_only(qapp):
    assert qapp.platformName() == "offscreen"


def test_default_window_generates_all_tests(win):
    assert win.state.printer["id"] == "elegoo-centauri-carbon"
    for tid, out in win.tests.results.items():
        assert out["ok"] and out["problems"] == [], tid
    names = {out["summary"]["name"] for out in win.tests.results.values()}
    assert "ECC_0.4_TempTower_PETG_260-220.gcode" in names


def test_steps_and_navigation(win, qapp):
    for i in range(5):
        win.go(i)
        qapp.processEvents()
        assert win.stack.currentIndex() == i and win.step_buttons.button(i).isChecked()
    win.go(0)
    win.next_btn.click()
    assert win.stack.currentIndex() == 1
    win.back_btn.click()
    assert win.stack.currentIndex() == 0


def test_theme_switch(win, qapp):
    from calib3d.ui import theme
    for i, name in enumerate(theme.THEMES):
        win.theme_combo.setCurrentIndex(i)
        qapp.processEvents()
        assert win.state.theme == name
        assert theme.palette(name)["accent"] in qapp.styleSheet()


def test_language_switch_rebuilds_texts(win, qapp):
    win.go(2)
    win.lang_combo.setCurrentIndex(1)
    qapp.processEvents()
    assert win.state.lang == "en" and win.windowTitle() == "Calibrate 3D Printer"
    assert win.stack.currentIndex() == 2
    assert win.step_buttons.button(0).text() == "1. Printer"
    assert wait(qapp, lambda: len(win.tests.results) == 10)
    tower = win.gen.now("temp_tower")
    assert "Temperature tower PETG 260-220" in tower["res"].text


def test_settings_survive_restart(win, qapp, _own_home):
    win.theme_combo.setCurrentIndex(2)
    win.lang_combo.setCurrentIndex(1)
    qapp.processEvents()
    from calib3d.ui.app import MainWindow
    w2 = MainWindow(remember=False)
    assert w2.state.theme == "light" and w2.state.lang == "en"
    w2.gen.round += 1
    w2.deleteLater()


def test_wrapped_labels_never_fixed_height(win, qapp):
    """qt-wrapped-label-height: wrapping labels only get a minimum height, and in the
    smallest window with fonts 10 % larger every label still has room for its text."""
    from PySide6.QtWidgets import QLabel
    win.resize(900, 620)
    for i in range(5):
        win.go(i)
        qapp.processEvents()
        for lab in win.findChildren(QLabel):
            if lab.wordWrap() and lab.isVisible():
                assert lab.maximumHeight() == 16777215, lab.text()[:40]
    qapp.setStyleSheet(qapp.styleSheet() + "\n* { font-size: 14px; }")
    for i in range(5):
        win.go(i)
        qapp.processEvents()
        for lab in win.findChildren(QLabel):
            if lab.wordWrap() and lab.isVisible() and lab.text() and lab.width() > 20:
                assert lab.heightForWidth(lab.width()) <= lab.height() + 1, lab.text()[:40]


def test_combo_arrow_drawn_and_no_fusion_square(win, qapp):
    """qt-combo-dropdown: the arrow is ours, the drop-down button draws nothing dark."""
    from PySide6.QtGui import QColor
    win.theme_combo.setCurrentIndex(2)        # light: a dark square would stand out
    qapp.processEvents()
    combo = win.lang_combo
    img = combo.grab().toImage()
    w, h = img.width(), img.height()
    bg = QColor(img.pixel(w // 3, h // 2))
    arrow = [QColor(img.pixel(x, h // 2)) for x in range(w - 20, w - 8)]
    assert any(abs(c.lightness() - bg.lightness()) > 40 for c in arrow), "no arrow"
    for y in range(4, h - 4):
        for x in range(w - 24, w - 2):
            c = QColor(img.pixel(x, y))
            if abs(x - (w - 14)) > 6 or abs(y - h / 2) > 5:
                assert c.lightness() > bg.lightness() - 40, (x, y)


def test_import_sample_fills_the_profile(win, qapp):
    r = win.printer.import_file(str(SAMPLES / "orca.gcode"))
    assert r["slicer"] == "orca"
    s = win.state
    assert s.printer["id"] == "imported" and s.printer["bed"]["x"] == 300.0
    assert s.material["first_layer_temp"] == 215
    assert win.printer.report.isVisible() and "PRINT_START" in win.printer.report.text()
    assert wait(qapp, lambda: len(win.tests.results) == 10)
    out = win.gen.now("cube")
    assert out["ok"] and out["problems"] == []
    assert "PRINT_START BED=60 HOTEND=215" in out["res"].text


def test_import_marks_missing_fields(win, qapp):
    win.printer.import_file(str(SAMPLES / "cura.gcode"))
    missing = [p for p, w in win.printer.fields.widgets.items() if w.property("missing")]
    assert {"bed.x", "bed.y", "nozzle"} <= set(missing)
    win.printer.fields.widgets["bed.x"].setValue(230)
    assert not win.printer.fields.widgets["bed.x"].property("missing")


def test_save_folder_and_zip(win, qapp, tmp_path):
    names = win.download.save_folder(str(tmp_path))
    assert len(names) == 10
    cc, petg = P.printer("elegoo-centauri-carbon"), P.material("petg")
    for tid in ("cube", "flow"):
        r = G.generate(cc, petg, tid)
        assert (tmp_path / r.name).read_bytes() == r.text.encode("utf-8")
    z = tmp_path / "all.zip"
    win.download.save_zip(str(z))
    with zipfile.ZipFile(z) as zf:
        assert sorted(zf.namelist()) == sorted(names)
        assert zf.read("ECC_0.4_Cube20_PETG.gcode") == (tmp_path / "ECC_0.4_Cube20_PETG.gcode").read_bytes()


def test_unchecked_tests_are_not_saved(win, qapp, tmp_path):
    win.go(2)
    win.tests.select_all(False)
    item = win.tests.list.item(0)
    from PySide6.QtCore import Qt
    item.setCheckState(Qt.CheckState.Checked)
    assert win.state.selected == ["first_layer"]
    assert win.download.save_folder(str(tmp_path)) == ["ECC_0.4_FirstLayer_PETG.gcode"]


def test_param_change_regenerates(win, qapp):
    win.go(2)
    win.tests.list.setCurrentRow(1)          # temperature tower
    qapp.processEvents()
    w = win.tests.param_widgets["t_end"]
    w.setValue(240)
    win.tests.timer.timeout.emit()
    assert wait(qapp, lambda: win.tests.results.get("temp_tower", {}).get("ok"))
    assert win.tests.results["temp_tower"]["summary"]["name"] == "ECC_0.4_TempTower_PETG_260-240.gcode"


def test_bad_param_shows_an_error(win, qapp):
    win.go(2)
    win.tests.list.setCurrentRow(1)
    qapp.processEvents()
    win.tests.param_widgets["t_end"].setValue(260)       # equals the start
    assert win.tests.param_err.isVisible() and "t_end" in win.tests.param_err.text()


def test_results_helper(win, qapp):
    win.go(4)
    win.results.inputs["pressure_advance"].setText("024")
    assert "0.024" in win.results.outputs["pressure_advance"].text()
    win.results.inputs["flow"].setText("abc")
    assert win.results.outputs["flow"].text()


def test_my_profile_save_and_delete(win, qapp, _own_home):
    win.printer.fields.widgets["name"].setText("My CC")
    win.printer.fields.widgets["name"].editingFinished.emit()
    win.printer.save_mine()
    assert win.state.printer["id"] == "my-my-cc" and win.state.printer.get("_user")
    assert (Path(_own_home) / "profiles" / "printers" / "my-my-cc.json").exists()
    win.printer.delete_mine()
    assert win.state.printer["id"] == "elegoo-centauri-carbon"


def test_profile_json_export_import(win, qapp, tmp_path):
    path = tmp_path / "p.json"
    win.printer.export_json(str(path))
    assert P.validate_printer(__import__("json").loads(path.read_text(encoding="utf-8"))) == []
    bad = tmp_path / "bad.json"
    bad.write_text('{"name": "x"}', encoding="utf-8")
    assert win.printer.import_json(str(bad))
    assert win.printer.import_json(str(path)) == []


def test_invalid_printer_field_shows_error(win, qapp):
    win.printer.fields.widgets["default_accel"].setValue(30000)     # above max 20000
    assert "default_accel" in win.printer.status.text()


def test_window_remembers_place(qapp, _own_home):
    from calib3d.ui.app import MainWindow
    w = MainWindow(remember=True)
    w.resize(1000, 700)
    w.move(40, 50)
    w.show()
    qapp.processEvents()
    w.close()
    qapp.processEvents()
    w.gen.round += 1
    saved = __import__("json").loads((Path(_own_home) / "window.json").read_text(encoding="utf-8"))
    assert (saved["width"], saved["height"]) == (1000, 700)
    from calib3d.ui.app import WINDOW_OPTS
    from calib3d.ui.window_state import restore, work_areas
    expect = restore(saved, work_areas(), WINDOW_OPTS)    # the offscreen screen may be small
    w2 = MainWindow(remember=True)
    assert (w2.width(), w2.height()) == (expect["width"], expect["height"])
    w2.gen.round += 1
    w2.deleteLater()
