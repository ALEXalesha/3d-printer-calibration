"""The five Paint themes in Qt: the same token values as web/css/themes.css (and Paint Pro,
the calculators). Surfaces are the page colour blended with the theme's "ink" the way the
glass layers are in CSS. tests/py/test_ui_theme.py compares the tokens with the CSS file."""
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QComboBox

THEMES = ["glass", "formal", "light", "night", "warm"]
DEFAULT = "glass"
DARK = {"glass", "formal", "night", "warm"}

# token values from themes.css: text, text-dim alpha, accent, accent-2, app-base, gradient,
# ink (R, G, B), glass-bg / glass-bg-strong / glass-border alphas
TOKENS = {
    "glass": dict(text="#f4f4f8", dim=0.62, accent="#5b8def", accent2="#9d5bef", base="#12101f",
                  grad=("#0e0c1a", "#1a1330", "#0c1024"), ink=(255, 255, 255), a=(0.08, 0.14, 0.18)),
    "formal": dict(text="#e6e8ec", dim=0.55, accent="#4a7ab8", accent2="#5c7fa6", base="#1f242e",
                   grad=("#1b1f27", "#232833", "#191d25"), ink=(255, 255, 255), a=(0.055, 0.10, 0.11)),
    "light": dict(text="#1b2030", dim=0.58, accent="#3a6fd8", accent2="#7a52d0", base="#e8ecf3",
                  grad=("#eff2f7", "#e3e8f0", "#dde3ed"), ink=(22, 26, 38), a=(0.045, 0.10, 0.14)),
    "night": dict(text="#dcdde3", dim=0.48, accent="#4668a8", accent2="#6a5aa0", base="#08090e",
                  grad=("#06070b", "#0b0d13", "#05060a"), ink=(255, 255, 255), a=(0.045, 0.085, 0.09)),
    "warm": dict(text="#f5ead9", dim=0.58, accent="#d08a3c", accent2="#b4562f", base="#1d1610",
                 grad=("#17110b", "#241a10", "#140f0a"), ink=(255, 236, 210), a=(0.07, 0.13, 0.16)),
}
DANGER = "#ff5b5b"
SUCCESS = "#2dd4a8"


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def blend(base, ink, alpha):
    b = _hex(base) if isinstance(base, str) else base
    return "#%02x%02x%02x" % tuple(round(b[i] * (1 - alpha) + ink[i] * alpha) for i in range(3))


def palette(name):
    t = TOKENS.get(name, TOKENS[DEFAULT])
    a1, a2, a3 = t["a"]
    p = {
        "bg": t["base"], "grad": t["grad"], "text": t["text"],
        # muted text a bit stronger than CSS text-dim: no backdrop blur here to help it
        "muted": blend(t["base"], _hex(t["text"]), max(t["dim"], 0.6)),
        "accent": t["accent"], "accent2": t["accent2"],
        # white on the warm ochre is 2.8:1 - dark text there, as on a warm button in Paint's light parts
        "accent_text": "#1d1610" if name == "warm" else "#ffffff",
        "surface": blend(t["base"], t["ink"], a1 * 1.6),
        "surface2": blend(t["base"], t["ink"], a2),
        "border": blend(t["base"], t["ink"], a3 * 1.3),
        "danger": DANGER, "success": SUCCESS, "dark": name in DARK,
        "canvas": "#1c1e24" if name != "light" else "#f4f6fa",
    }
    if name == "light":
        p["surface"] = "#f7f9fc"
        p["surface2"] = "#ffffff"
        p["danger"] = "#d43c3c"
        p["success"] = "#138a6c"
    return p


def qss(name):
    p = palette(name)
    g = p["grad"]
    return f"""
* {{ font-family: "Segoe UI", "Noto Sans", sans-serif; font-size: 13px; color: {p['text']}; }}
QMainWindow, QWidget#root {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {g[0]}, stop:0.5 {g[1]}, stop:1 {g[2]});
}}
QWidget#page, QScrollArea, QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollArea {{ border: none; }}
QLabel, QCheckBox, QRadioButton {{ background: transparent; }}
QLabel#title {{ font-size: 22px; font-weight: 700; }}
QLabel#subtitle, QLabel#muted, QLabel#hint {{ color: {p['muted']}; }}
QLabel#hint {{ font-size: 12px; }}
QLabel#section {{ font-size: 15px; font-weight: 600; }}
QLabel#badgeOk {{ color: {p['success']}; font-weight: 600; }}
QLabel#badgeWarn {{ color: {p['danger']}; font-weight: 600; }}
QLabel#error {{ color: {p['danger']}; }}
QLabel#ok {{ color: {p['success']}; }}
QLabel#big {{ font-size: 16px; font-weight: 600; }}
QFrame#card {{ background: {p['surface']}; border: 1px solid {p['border']}; border-radius: 12px; }}
QFrame#importCard {{ background: {p['surface']}; border: 2px solid {p['accent']}; border-radius: 14px; }}
QPushButton {{
    background: {p['surface2']}; border: 1px solid {p['border']}; border-radius: 9px; padding: 7px 14px;
}}
QPushButton:hover {{ border-color: {p['accent']}; }}
QPushButton:pressed {{ background: {p['surface']}; }}
QPushButton:disabled {{ color: {p['muted']}; }}
QPushButton#primary {{
    background: {p['accent']}; color: {p['accent_text']}; border: 1px solid {p['accent']}; font-weight: 600;
}}
QPushButton#primary:hover {{ background: {p['accent2']}; border-color: {p['accent2']}; }}
QPushButton#big {{
    background: {p['accent']}; color: {p['accent_text']}; border: 1px solid {p['accent']};
    font-size: 15px; font-weight: 600; padding: 11px 20px;
}}
QPushButton#step {{
    background: transparent; border: none; border-bottom: 2px solid transparent; border-radius: 0;
    padding: 9px 14px; color: {p['muted']}; font-size: 14px;
}}
QPushButton#step:checked {{ color: {p['text']}; border-bottom: 2px solid {p['accent']}; font-weight: 600; }}
QPushButton#step:hover {{ color: {p['text']}; }}
QLineEdit, QPlainTextEdit, QAbstractSpinBox, QComboBox {{
    background: {p['surface2']}; border: 1px solid {p['border']}; border-radius: 7px; padding: 5px 8px;
    selection-background-color: {p['accent']}; selection-color: {p['accent_text']};
}}
QLineEdit:focus, QPlainTextEdit:focus, QAbstractSpinBox:focus, QComboBox:focus {{ border-color: {p['accent']}; }}
*[missing="true"] {{ border: 2px solid {p['danger']}; }}
QPlainTextEdit {{ font-family: "Cascadia Mono", Consolas, monospace; font-size: 12px; }}
QComboBox {{ padding-right: 26px; }}
QComboBox::drop-down {{ border: none; width: 24px; background: transparent; }}
QComboBox::down-arrow {{ image: none; width: 0; height: 0; }}
QComboBox QAbstractItemView {{
    background: {p['surface2']}; border: 1px solid {p['border']}; outline: none;
    selection-background-color: {p['accent']}; selection-color: {p['accent_text']};
}}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{
    width: 17px; height: 17px; border-radius: 5px; border: 1px solid {p['border']}; background: {p['surface2']};
}}
QCheckBox::indicator:checked {{ background: {p['accent']}; border-color: {p['accent']}; image: none; }}
QListWidget {{ background: {p['surface']}; border: 1px solid {p['border']}; border-radius: 10px; outline: none; padding: 4px; }}
QListWidget::item {{ padding: 7px 6px; border-radius: 7px; }}
QListWidget::item:selected {{ background: {p['surface2']}; color: {p['text']}; border: 1px solid {p['accent']}; }}
QTableWidget {{
    background: {p['surface']}; border: 1px solid {p['border']}; border-radius: 10px; gridline-color: {p['border']};
    selection-background-color: {p['surface2']}; selection-color: {p['text']};
}}
QHeaderView::section {{ background: {p['surface2']}; color: {p['muted']}; border: none; padding: 6px; font-weight: 600; }}
QTableCornerButton::section {{ background: {p['surface2']}; border: none; }}
QSlider::groove:horizontal {{ height: 6px; background: {p['surface2']}; border-radius: 3px; }}
QSlider::sub-page:horizontal {{ background: {p['accent']}; border-radius: 3px; }}
QSlider::handle:horizontal {{ background: {p['text']}; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {p['border']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {p['border']}; border-radius: 4px; min-width: 30px; }}
QToolTip {{ background: {p['surface2']}; color: {p['text']}; border: 1px solid {p['border']}; }}
"""


class Combo(QComboBox):
    """Combo box with its own arrow. The QSS drop-down button is transparent (Fusion drew a
    square over the rounded field) and QSS cannot draw a triangle, so it is drawn here."""

    arrow_color = "#9aa3b5"

    def paintEvent(self, event):
        super().paintEvent(event)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(self.arrow_color))
        cx, cy = self.width() - 14, self.height() / 2
        p.drawPolygon([QPointF(cx - 5, cy - 2.5), QPointF(cx + 5, cy - 2.5), QPointF(cx, cy + 3.5)])
        p.end()
