"""window_state.restore - the same rule as window-state.js of the calculators and Paint."""
from hypothesis import given, strategies as st

from calib3d.ui.window_state import restore

OPTS = {"width": 1180, "height": 800, "minWidth": 900, "minHeight": 620}
SCREEN = [{"x": 0, "y": 0, "width": 1920, "height": 1040}]


def test_garbage_gives_default():
    for bad in (None, "x", 5, [], {"width": "a"}, {"width": float("nan"), "height": 3}):
        assert restore(bad, SCREEN, OPTS) == {"width": 1180, "height": 800, "maximized": False}


def test_off_screen_window_is_centred():
    r = restore({"x": 5000, "y": 5000, "width": 1000, "height": 700}, SCREEN, OPTS)
    assert "x" not in r and r["width"] == 1000


def test_too_big_and_too_small():
    assert restore({"width": 5000, "height": 5000}, SCREEN, OPTS)["width"] == 1920
    assert restore({"width": 10, "height": 10}, SCREEN, OPTS)["width"] == 900


@given(st.integers(-3000, 3000), st.integers(-3000, 3000), st.integers(100, 4000), st.integers(100, 3000))
def test_title_bar_always_reachable(x, y, w, h):
    r = restore({"x": x, "y": y, "width": w, "height": h}, SCREEN, OPTS)
    assert r["width"] >= 900 and r["height"] >= 620
    if "x" in r:
        assert 0 <= r["x"] and r["x"] + 80 <= 1920 and 0 <= r["y"] <= 1040 - 38 or r["height"] > 1040
