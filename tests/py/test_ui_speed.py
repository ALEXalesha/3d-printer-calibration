"""The window stays responsive: a heartbeat timer on the UI thread must never wait longer
than the budget while the usual actions run (offscreen).

Alexey 03.10: "the Python version lags a bit". Measured (tools/profile_ui.py): the
generation of all ten tests ran in a Python thread and held the interpreter lock - the
event loop stalled up to 750 ms after every change; the front view repainted 37,000 lines
in Python on every paint (43 ms each). The budget below is what a person does not notice
as a freeze.
"""
import functools
import time
from pathlib import Path

import pytest

BUDGET_MS = 100        # longest allowed stall of the event loop
SAMPLES = Path(__file__).resolve().parents[1] / "import"


class Heartbeat:
    def __init__(self):
        from PySide6.QtCore import QElapsedTimer, QTimer
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


def best_of_three(test):
    """Up to three tries. A stall of our own (the interpreter lock held by generation, a slow
    repaint) comes back on every try; one caused by another program on a busy PC does not.
    10.10, the full suite next to other agents' work: 176 ms once, under 100 ms right after."""
    @functools.wraps(test)
    def wrapper(*args, **kwargs):
        for attempt in range(3):
            try:
                return test(*args, **kwargs)
            except AssertionError:
                if attempt == 2:
                    raise
    return wrapper


def settle(app, win, seconds=60):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        if len(win.tests.results) == 10 and not win.tests.timer.isActive():
            break
        time.sleep(0.002)
    end = time.monotonic() + 0.3
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.002)
    assert len(win.tests.results) == 10, "generation did not finish"


@pytest.fixture
def win(qapp):
    from calib3d.ui.app import MainWindow
    w = MainWindow(remember=False)
    w.resize(1180, 800)
    w.show()
    settle(qapp, w)
    yield w
    w.close()
    w.deleteLater()
    qapp.processEvents()


def run(app, win, hb, action):
    settle(app, win)
    hb.reset()
    action()
    settle(app, win)
    return hb.worst


@best_of_three
def test_background_generation_does_not_freeze_the_window(qapp, win):
    hb = Heartbeat()
    worst = 0
    for i in range(3):          # each edit regenerates all ten tests
        w = win.printer.fields.widgets["retract.length"]
        worst = max(worst, run(qapp, win, hb, lambda: w.setValue(w.value() + 0.1)))
    assert worst < BUDGET_MS, f"event loop stalled {worst} ms while generating"


@best_of_three
def test_switching_tests_and_previews(qapp, win):
    hb = Heartbeat()
    win.go(2)
    worst = 0
    for row in (1, 6, 2, 1):    # temp tower, overhangs, flow, tower again (front views)
        worst = max(worst, run(qapp, win, hb, lambda row=row: win.tests.list.setCurrentRow(row)))
    assert worst < BUDGET_MS, f"switching tests stalled {worst} ms"


@best_of_three
def test_typing_import_and_pages(qapp, win):
    hb = Heartbeat()
    ed = win.printer.fields.widgets["start_gcode"]

    def typing():
        for ch in "; note":
            ed.insertPlainText(ch)
            qapp.processEvents()
    worst = run(qapp, win, hb, typing)
    worst = max(worst, run(qapp, win, hb, lambda: win.printer.import_file(str(SAMPLES / "orca.gcode"))))
    for i in range(5):
        worst = max(worst, run(qapp, win, hb, lambda i=i: win.go(i)))
    assert worst < BUDGET_MS, f"stalled {worst} ms"


@best_of_three
def test_clicking_around_while_generating(qapp, win):
    """The real case: an edit starts the regeneration of all ten tests (seconds of CPU),
    and the person keeps clicking meanwhile."""
    hb = Heartbeat()
    settle(qapp, win)
    w = win.printer.fields.widgets["retract.length"]
    w.setValue(w.value() + 0.1)
    win.tests.timer.timeout.emit()            # start now, no debounce wait
    hb.reset()
    for step in (2, 0, 2, 1, 3, 2):
        win.go(step)
        if step == 2:
            win.tests.list.setCurrentRow((win.tests.list.currentRow() + 1) % 10)
        end = time.monotonic() + 0.4
        while time.monotonic() < end:
            qapp.processEvents()
            time.sleep(0.002)
    worst = hb.worst
    settle(qapp, win)
    assert worst < BUDGET_MS, f"clicks during generation stalled {worst} ms"


@best_of_three
def test_language_and_theme_switch_budget(qapp, win):
    """Rebuilding the pages for another language and restyling for another theme are one-off
    actions; they get a larger budget, but no second restyle and no lock contention."""
    hb = Heartbeat()
    lang = run(qapp, win, hb, lambda: win.lang_combo.setCurrentIndex(1))
    theme = run(qapp, win, hb, lambda: win.theme_combo.setCurrentIndex(2))
    assert lang < 600 and theme < 600, (lang, theme)
