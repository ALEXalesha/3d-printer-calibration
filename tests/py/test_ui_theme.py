"""The Qt themes are the Paint themes: same tokens as web/css/themes.css; readable contrast."""
import re
from pathlib import Path

import pytest

from calib3d.ui import theme

CSS = (Path(__file__).resolve().parents[2] / "web" / "css" / "themes.css").read_text(encoding="utf-8")


def block(name):
    sel = r":root\s*\{" if name == "glass" else r':root\[data-theme="%s"\]\s*\{' % name
    m = re.search(sel + r"(.*?)\n\}", CSS, re.S)
    assert m, name
    return dict(re.findall(r"--([a-z0-9-]+):\s*([^;]+);", m.group(1)))


@pytest.mark.parametrize("name", theme.THEMES)
def test_tokens_match_css(name):
    css, t = block(name), theme.TOKENS[name]
    assert css["text"].strip() == t["text"]
    assert css["accent"].strip() == t["accent"]
    assert css["accent-2"].strip() == t["accent2"]
    assert css["app-base"].strip() == t["base"]


def lum(hexc):
    c = [int(hexc.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


@pytest.mark.parametrize("name", theme.THEMES)
def test_contrast(name):
    p = theme.palette(name)
    for bg in (p["surface"], p["surface2"], p["bg"]):
        assert contrast(p["text"], bg) >= 7, (name, bg)
        assert contrast(p["muted"], bg) >= 3.5, (name, bg)
    assert contrast(p["accent_text"], p["accent"]) >= 2.9
    assert contrast(p["danger"], p["surface"]) >= 3
