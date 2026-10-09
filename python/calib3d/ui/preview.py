"""Top and front views of a test (the reference's preview(), drawn with QPainter)."""
from PySide6.QtCore import QLineF, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..core.preview import COLORS


class PreviewView(QWidget):
    """mode "top": the bed from above with the first layer and the labels;
    mode "front": X-Z projection of the front face."""

    def __init__(self, mode, parent=None):
        super().__init__(parent)
        self.mode = mode
        self.data = None
        self.bg = QColor("#1c1e24")
        self.grid = QColor("#2c2f38")
        self.setMinimumSize(220, 160)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def sizeHint(self):
        return QSize(360, 260)

    def set_data(self, data):
        self.data = data
        self._cache = None
        self.update()

    def set_colors(self, bg, grid):
        self.bg, self.grid = QColor(bg), QColor(grid)
        self._cache = None
        self.update()

    def paintEvent(self, event):
        # Drawing the lines is Python work (37,000 lines for a tower front view, 40-70 ms);
        # it is done once per data and size into a pixmap, every other paint is a copy.
        dpr = self.devicePixelRatioF()
        key = (self.width(), self.height(), dpr)
        cache = getattr(self, "_cache", None)
        if cache is None or cache[0] != key:
            pm = QPixmap(max(1, round(self.width() * dpr)), max(1, round(self.height() * dpr)))
            pm.setDevicePixelRatio(dpr)
            pm.fill(Qt.GlobalColor.transparent)
            p = QPainter(pm)
            self.render_into(p)
            p.end()
            self._cache = (key, pm)
        p = QPainter(self)
        p.drawPixmap(0, 0, self._cache[1])
        p.end()

    def lines(self):
        if not self.data:
            return []
        return self.data["top"] if self.mode == "top" else (self.data["front"] or [])

    def render_into(self, p):
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(self.bg)
        p.drawRoundedRect(r, 10, 10)
        if not self.data:
            return
        bed = self.data["bed"]
        if self.mode == "top":
            if bed["origin"] == "center":
                x0, y0, x1, y1 = -bed["x"] / 2, -bed["y"] / 2, bed["x"] / 2, bed["y"] / 2
            else:
                x0, y0, x1, y1 = 0.0, 0.0, bed["x"], bed["y"]
        else:
            segs = self.lines()
            if not segs:
                return
            xs = [c for s in segs for c in (s[0], s[2])]
            x0, x1 = min(xs) - 5, max(xs) + 5
            y0, y1 = 0.0, max(s[1] for s in segs) + 5
        pad = 10
        sw = (r.width() - 2 * pad) / max(1e-6, x1 - x0)
        sh = (r.height() - 2 * pad) / max(1e-6, y1 - y0)
        s = min(sw, sh)
        ox = r.left() + pad + ((r.width() - 2 * pad) - s * (x1 - x0)) / 2
        oy = r.top() + pad + ((r.height() - 2 * pad) - s * (y1 - y0)) / 2

        def pt(x, y):
            return QPointF(ox + (x - x0) * s, oy + (y1 - y) * s)

        if self.mode == "top":
            p.setPen(QPen(self.grid, 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            if bed["shape"] == "round":
                c = pt(0, 0)
                p.drawEllipse(c, bed["x"] / 2 * s, bed["y"] / 2 * s)
            else:
                p.drawRect(QRectF(pt(x0, y1), pt(x1, y0)))
        else:
            p.setPen(QPen(self.grid, 1))
            p.drawLine(pt(x0, 0), pt(x1, 0))
        width = max(1.0, min(2.0, s * 0.45))
        pens = {k: QPen(QColor(v), width) for k, v in COLORS.items()}
        default = QPen(QColor("#ffffff"), width)
        # Drawn in order (later lines cover earlier ones), consecutive lines of one colour
        # in one call: a Python loop of drawLine calls took 40-100 ms for a tower front view.
        batch, kind_now = [], None
        for x_a, y_a, x_b, y_b, kind in self.lines():
            if kind != kind_now:
                if batch:
                    p.setPen(pens.get(kind_now, default))
                    p.drawLines(batch)
                batch, kind_now = [], kind
            batch.append(QLineF(ox + (x_a - x0) * s, oy + (y1 - y_a) * s, ox + (x_b - x0) * s, oy + (y1 - y_b) * s))
        if batch:
            p.setPen(pens.get(kind_now, default))
            p.drawLines(batch)
