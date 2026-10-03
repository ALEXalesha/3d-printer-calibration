"""Draws the app icon (a nozzle over a temperature tower) and writes assets/icon.png,
assets/icon.ico and web/favicon.png. Offscreen Qt, no extra libraries."""
import os
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath  # noqa: E402


def render(size):
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size / 256
    bg = QLinearGradient(0, 0, size, size)
    bg.setColorAt(0, QColor("#5b8def"))
    bg.setColorAt(1, QColor("#9d5bef"))
    path = QPainterPath()
    path.addRoundedRect(QRectF(8 * s, 8 * s, 240 * s, 240 * s), 52 * s, 52 * s)
    p.fillPath(path, bg)
    # tower: layers getting cooler upwards
    colors = ["#ff6b4a", "#ff8a4a", "#ffab4a", "#ffd04a", "#e8f0ff"]
    for i, c in enumerate(colors):
        y = 196 - i * 26
        p.setBrush(QColor(c))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(70 * s, y * s, 116 * s, 20 * s), 6 * s, 6 * s)
    # nozzle
    p.setBrush(QColor("#1b2030"))
    p.drawPolygon([QPointF(108 * s, 40 * s), QPointF(148 * s, 40 * s), QPointF(140 * s, 76 * s),
                   QPointF(116 * s, 76 * s)])
    p.drawPolygon([QPointF(118 * s, 76 * s), QPointF(138 * s, 76 * s), QPointF(128 * s, 90 * s)])
    p.end()
    return img


def png_bytes(img):
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    return bytes(buf.data())


def write_ico(path, sizes=(16, 24, 32, 48, 64, 128, 256)):
    """ICO with PNG-compressed images (Windows Vista+ reads them)."""
    images = [png_bytes(render(n)) for n in sizes]
    head = struct.pack("<HHH", 0, 1, len(images))
    offset = 6 + 16 * len(images)
    entries, data = b"", b""
    for n, png in zip(sizes, images):
        entries += struct.pack("<BBBBHHII", n % 256, n % 256, 0, 0, 1, 32, len(png), offset + len(data))
        data += png
    Path(path).write_bytes(head + entries + data)


def main():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)  # noqa: F841
    (ROOT / "assets").mkdir(exist_ok=True)
    render(512).save(str(ROOT / "assets" / "icon.png"))
    render(64).save(str(ROOT / "web" / "favicon.png"))
    write_ico(ROOT / "assets" / "icon.ico")
    print("assets/icon.png, assets/icon.ico, web/favicon.png")


if __name__ == "__main__":
    main()
