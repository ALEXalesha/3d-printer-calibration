"""Калибровочные G-code для Elegoo Centauri Carbon (сопло 0.4, прошивка на Klipper).

    python calibration.py            - все 20 файлов (10 тестов для PETG и PLA)
    python calibration.py --preview  - ещё и картинки-проверки в preview/

Начальный и конечный код - как в настоящей печати на этом принтере (ElegooSlicer 1.5.3.5,
профиль «Elegoo Centauri Carbon 0.4 nozzle», 21.09.2026): прогрев, M729 (чистка сопла),
M6211 (подача CANVAS), линия прочистки Elegoo. Пластик - настройки пресетов Алексея.

Башня температур: 9 уровней по 10 мм, горячий внизу. На уровне две колонны 14x10 мм с зазором
20 мм: переезды между ними показывают нити, мост поверх зазора - как пластик держит мост,
стенки - качество поверхности. Температура уровня выдавлена цифрами на передней грани левой
колонны (передняя - к дверце, меньший Y).

Линии опережения (pressure advance): 17 линий, значение от 0.000 до 0.080 с шагом 0.005.
Каждая линия: 20 мм медленно, 40 мм быстро, 20 мм медленно. Справа - значение в тысячных
(«024» = 0.024). Лучшая линия - ровной толщины без утолщений и провалов на переходах.
"""
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = Path(r"C:\Users\you\All_3d\gcode")
PREVIEW = HERE / "preview"

FIL_AREA = math.pi * (1.75 / 2) ** 2
BED = 256.0

# Пластики - как в пресетах Алексея (Generic PETG / Generic PLA @Elegoo Centauri, копии).
MATERIALS = {
    "PETG": dict(type="PETG", temps=[260, 255, 250, 245, 240, 235, 230, 225, 220], first_temp=255,
                 bed=80, flow=1.0, mvs=10.0, fan=0.5, bridge_fan=1.0, fan_off_layers=3,
                 min_layer_time=8.0, pa_default=0.02),
    "PLA": dict(type="PLA", temps=[230, 225, 220, 215, 210, 205, 200, 195, 190], first_temp=210,
                bed=60, flow=0.98, mvs=21.0, fan=1.0, bridge_fan=1.0, fan_off_layers=1,
                min_layer_time=4.0, pa_default=0.024),
}

RETRACT, RETRACT_F, ZHOP = 0.8, 1800, 0.4
TRAVEL_F = 18000
ACCEL = 5000


def area(w, h):
    """Сечение валика: прямоугольник со скруглёнными краями, как считает слайсер."""
    return (w - h) * h + math.pi * (h / 2) ** 2


class Gcode:
    def __init__(self, mat):
        self.mat = mat
        self.lines = []
        self.x = self.y = 0.0
        self.z = 0.0
        self.retracted = False
        self.segments = []  # (x1, y1, x2, y2, z, kind) - для картинок и проверок
        self.time = 0.0
        self.e_total = 0.0
        self.retract_len = RETRACT

    def out(self, s):
        self.lines.append(s)

    def retract(self):
        if not self.retracted:
            self.out(f"G1 E-{self.retract_len:.2f} F{RETRACT_F}")
            self.time += self.retract_len / (RETRACT_F / 60)
            self.retracted = self.retract_len

    def unretract(self):
        if self.retracted:
            self.out(f"G1 E{self.retracted:.2f} F{RETRACT_F}")  # вернуть ровно столько, сколько втянули
            self.time += self.retracted / (RETRACT_F / 60)
            self.retracted = False

    def travel(self, x, y, hop=True):
        d = math.hypot(x - self.x, y - self.y)
        if d < 0.01:
            return
        long_move = d > 2.0
        if long_move:
            self.retract()
            if hop:
                self.out(f"G1 Z{self.z + ZHOP:.3f} F9000")
        self.out(f"G1 X{x:.3f} Y{y:.3f} F{TRAVEL_F}")
        if long_move and hop:
            self.out(f"G1 Z{self.z:.3f} F9000")
        self.time += d / (TRAVEL_F / 60) + (0.1 if long_move else 0)
        self.x, self.y = x, y

    def extrude(self, x, y, w, h, speed, kind, flow=None, cap=True):
        d = math.hypot(x - self.x, y - self.y)
        if d < 0.01:
            return
        self.unretract()
        e = d * area(w, h) / FIL_AREA * (flow if flow is not None else self.mat["flow"])
        if cap:
            speed = min(speed, self.mat["mvs"] * 0.9 / area(w, h))  # не выше расхода пластика
        self.out(f"G1 X{x:.3f} Y{y:.3f} E{e:.5f} F{speed * 60:.0f}")
        self.segments.append((self.x, self.y, x, y, self.z, kind))
        self.time += d / speed
        self.e_total += e
        self.x, self.y = x, y

    def path(self, pts, w, h, speed, kind, closed=False, flow=None):
        if not pts:
            return
        self.travel(*pts[0])
        for p in pts[1:]:
            self.extrude(p[0], p[1], w, h, speed, kind, flow)
        if closed:
            self.extrude(pts[0][0], pts[0][1], w, h, speed, kind, flow)

    def fan(self, frac):
        self.out(f"M106 S{round(255 * frac)}")

    def layer(self, n, z, h, total):
        self.out(";LAYER_CHANGE")
        self.out(f";Z:{z:.2f}")
        self.out(f";HEIGHT:{h:.2f}")
        self.out(f";LAYER:{n}")
        self.retract()
        self.out(f"G1 Z{z:.3f} F9000")
        self.out(f"SET_PRINT_STATS_INFO TOTAL_LAYER={total} CURRENT_LAYER={n + 1}")
        self.z = z


# ---------- начало и конец - как в настоящей печати ----------

def start_gcode(g, first_temp, title, total_layers, max_z):
    m = g.mat
    mvs = m["mvs"]
    f1 = min(6000, max(900, mvs / 0.5 / 0.3 * 60))
    f2 = min(12000, max(1200, mvs / 0.5 / 0.3 * 60))
    g.out("; HEADER_BLOCK_START")
    g.out(f"; generated by calibration.py ({title})")
    g.out(f"; total layer number: {total_layers}")
    g.out("; filament_diameter: 1.75")
    g.out(f"; max_z_height: {max_z:.2f}")
    g.out("; HEADER_BLOCK_END")
    g.out("")
    g.out("; EXECUTABLE_BLOCK_START")
    g.out("M106 S0 ; disable fan")
    g.out("M106 P2 S0 ; disable additional fan")
    g.out(";===== CC_START_GCODE (как ElegooSlicer, профиль Centauri Carbon 0.4) =====")
    g.out(";printer_model:Elegoo Centauri Carbon")
    g.out(f";initial_filament:{m['type']}")
    g.out(f";bed_level_temp:{m['bed']}")
    for s in ["M400 ; wait for buffer to clear", "M220 S100 ;Set the feed speed to 100%",
              "M221 S100 ;Set the flow rate to 100%", "M104 S140", f"M140 S{m['bed']}", "G90", "M83",
              "G28 ;home", "M729 ;Clean Nozzle", f"M190 S{m['bed']}", "", f"M109 S{first_temp}",
              f"M6211 A1 L200 T0 Q{first_temp} R{first_temp} S{first_temp}", "T0"]:
        g.out(s)
    if m["type"] == "PLA" and m["bed"] > 50:
        g.out("M106 P3 S255 ;Prevent PLA from jamming")
    g.out(f"M204 S{ACCEL} ;acceleration")
    g.out("G1 X128 Y-1.2 F20000")
    g.out("G1 Z0.3 F900")
    g.out("G90")
    g.out("M83")
    g.out("G92 E0 ;Reset Extruder")
    g.out(f"G1 F{f1:.0f}")
    for s in ["G1 X0 E10.156 ;Draw the first line", "G1 Y98.8 E7.934", "G1 X0.9 Y100 E0.1",
              "G1 Y-0.3 E7.934", "G1 X78 E6.284"]:
        g.out(s)
    for x, f in ((98, 0.2 * f2), (118, f2), (138, 0.2 * f2), (158, f2), (178, f2)):
        g.out(f"G1 F{f:.0f}")
        g.out(f"G1 X{x} E2")
    g.out("G3 I-1 J0 Z0.6 F1200.0 ;Move to side a little")
    g.out("G1 F20000")
    g.out("G92 E0 ;Reset Extruder")
    g.out(f"SET_PRINT_STATS_INFO TOTAL_LAYER={total_layers} CURRENT_LAYER=0")
    g.out(f";LAYER_COUNT:{total_layers}")
    g.x, g.y, g.z = 177.0, -1.2, 0.6
    g.time += 240  # нагрев, парковка, чистка и прочистка - примерно
    g.e_total += 10.156 + 7.934 * 2 + 0.1 + 6.284 + 10


def end_gcode(g, max_z):
    g.out("M106 S0 ; disable fan")
    g.out(";===== CC_END_GCODE =====")
    for s in ["M400 ; wait for buffer to clear", "M140 S0 ;Turn-off bed", "M106 S255 ;Cooling nozzle",
              "M83", "G92 E0 ; zero the extruder", "G1 E-0.8 F1800",
              f"G2 I1 J0 Z{max_z + 0.5:.2f} F3000 ; lower z a little", "G90",
              (f"G1 Z{min(max_z + 50, 256.5):.2f} F20000" if max_z > 100 else "G1 Z100 F20000") + " ; Move print head up",
              "M204 S5000", "M749", "M204 S5000", "M400", "M83", "G1 X202 F20000", "M400",
              "G1 Y250 F20000", "G1 Y264.5 F1200", "M400", "G92 E0", "M104 S0 ;Turn-off hotend",
              "M140 S0 ;Turn-off bed", "M106 S0 ; turn off fan", "M106 P2 S0 ; turn off remote part cooling fan",
              "M106 P3 S0 ; turn off chamber cooling fan", "M84 ;Disable all steppers"]:
        g.out(s)
    g.out("; EXECUTABLE_BLOCK_END")


def footer(g, title):
    grams = g.e_total * FIL_AREA / 1000 * (1.27 if g.mat["type"] == "PETG" else 1.24)
    h, m = divmod(round(g.time / 60), 60)
    g.out("")
    g.out(f"; {title}")
    g.out(f"; filament used [mm] = {g.e_total:.2f}")
    g.out(f"; filament used [g] = {grams:.2f}")
    g.out(f"; estimated printing time (normal mode) = {h}h {m}m")
    return grams


# ---------- прямоугольники: стенки и заполнение ----------

def rect_loop(x1, y1, x2, y2):
    return [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]


def perimeters(g, box, w, h, speed_outer, speed_inner, n=2, kind="wall"):
    x1, y1, x2, y2 = box
    for i in reversed(range(n)):  # внутренняя стенка первой, наружная последней
        o = w / 2 + i * w
        g.path(rect_loop(x1 + o, y1 + o, x2 - o, y2 - o), w, h,
               speed_outer if i == 0 else speed_inner, kind if i == 0 else "inner", closed=True)


def fill(g, box, w, h, speed, along_x, spacing, kind, flow=None):
    """Заполнение линиями зигзагом, с заходом на внутреннюю стенку на 15%."""
    x1, y1, x2, y2 = box
    lines = []
    if along_x:
        y = y1 + w / 2
        while y <= y2 - w / 2 + 1e-6:
            lines.append(((x1, y), (x2, y)))
            y += spacing
    else:
        x = x1 + w / 2
        while x <= x2 - w / 2 + 1e-6:
            lines.append(((x, y1), (x, y2)))
            x += spacing
    for i, (a, b) in enumerate(lines):
        if i % 2:
            a, b = b, a
        if i == 0:
            g.travel(*a)
        else:
            # связка вдоль края: короткая, печатается
            g.extrude(a[0], a[1], w, h, speed, kind, flow)
        g.extrude(b[0], b[1], w, h, speed, kind, flow)


# ---------- цифры: семь сегментов ----------

SEGS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
        "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def seg_boxes(W, H, S):
    """Сегменты цифры шириной W, высотой H, толщиной штриха S: (x1, x2, v1, v2) - v вертикаль."""
    return {"a": (0, W, H - S, H), "g": (0, W, (H - S) / 2, (H + S) / 2), "d": (0, W, 0, S),
            "f": (0, S, H / 2, H), "b": (W - S, W, H / 2, H), "e": (0, S, 0, H / 2), "c": (W - S, W, 0, H / 2)}


def text_intervals(text, x0, v, W=3.6, H=6.0, S=1.2, gap=1.0):
    """Отрезки по X, где на высоте v (от низа строки) есть штрих текста."""
    boxes = seg_boxes(W, H, S)
    out = []
    for i, ch in enumerate(text):
        dx = x0 + i * (W + gap)
        spans = sorted((dx + b[0], dx + b[1]) for s in SEGS[ch] for b in [boxes[s]] if b[2] <= v <= b[3])
        for a, b in spans:  # слить перекрывающиеся
            if out and a <= out[-1][1] + 1e-6 and out[-1][0] >= dx - 1e-6:
                out[-1] = (out[-1][0], max(out[-1][1], b))
            else:
                out.append((a, b))
    return out


def flat_digit_strokes(ch, x0, y0, W=2.0, H=3.2):
    """Цифра на столе одной линией на сегмент: список отрезков ((x, y), (x, y))."""
    p = {"a": ((0, H), (W, H)), "g": ((0, H / 2), (W, H / 2)), "d": ((0, 0), (W, 0)),
         "f": ((0, H / 2), (0, H)), "b": ((W, H / 2), (W, H)), "e": ((0, 0), (0, H / 2)), "c": ((W, 0), (W, H / 2))}
    order = "fabgedc"
    return [((x0 + p[s][0][0], y0 + p[s][0][1]), (x0 + p[s][1][0], y0 + p[s][1][1])) for s in order if s in SEGS[ch]]


# ---------- башня температур ----------

def temp_tower(mat_name):
    m = MATERIALS[mat_name]
    g = Gcode(m)
    H = 0.2
    W = 0.45
    LEVEL = 10.0
    SLAB = 1.6                       # мост и перекрытие поверх уровня
    BASE = 0.6                       # подложка: 3 слоя
    A = (104.0, 123.0, 118.0, 133.0)  # левая колонна (с подписью)
    B = (138.0, 123.0, 152.0, 133.0)  # правая колонна
    slab_box = (A[0], A[1], B[2], B[3])
    base_box = (96.0, 116.0, 160.0, 140.0)
    temps = m["temps"]
    layers_per_level = round(LEVEL / H)
    total = round(BASE / H) + layers_per_level * len(temps)
    max_z = BASE + LEVEL * len(temps)
    title = f"Башня температур {mat_name} {temps[0]}-{temps[-1]}"
    start_gcode(g, temps[0], title, total, max_z)

    outer, inner, infill = 60, 100, 120
    n = 0
    # подложка
    for i in range(round(BASE / H)):
        z = H * (i + 1)
        g.layer(n, z, H, total)
        w = 0.5 if i == 0 else W
        sp = 40 if i == 0 else infill
        perimeters(g, base_box, w, H, 40 if i == 0 else outer, sp, kind="base")
        o = 2 * w
        fill(g, (base_box[0] + o - 0.15 * w, base_box[1] + o - 0.15 * w, base_box[2] - o + 0.15 * w, base_box[3] - o + 0.15 * w),
             w, H, sp, i % 2 == 0, w, "base")
        n += 1

    for lvl, t in enumerate(temps):
        g.out(f"; ===== уровень {lvl + 1}: {t} C =====")
        g.out(f"M104 S{t}")
        label = str(t)
        for k in range(layers_per_level):
            z = BASE + lvl * LEVEL + H * (k + 1)
            local = H * (k + 1)
            g.layer(n, z, H, total)
            if n == m["fan_off_layers"]:
                g.fan(m["fan"])
            layer_start = len(g.lines)
            t0 = g.time
            if local <= LEVEL - SLAB + 1e-6:
                for box, has_label in ((A, True), (B, False)):
                    perimeters(g, box, W, H, outer, inner)
                    if has_label:
                        v = local - H / 2 - 1.8   # подпись: полоса 1.8..7.8 мм от низа уровня
                        if 0 <= v <= 6.0:
                            x0 = A[0] + (14.0 - (3 * 3.6 + 2 * 1.0)) / 2
                            for a, b in text_intervals(label, x0, v):
                                for yy in (A[1] - 0.6, A[1] - 0.15):
                                    xa, xb = a + W / 2, b - W / 2
                                    if xb - xa < 0.1:
                                        xa, xb = (a + b) / 2 - 0.05, (a + b) / 2 + 0.05
                                    g.travel(xa, yy, hop=False)
                                    g.extrude(xb, yy, W, H, 20, "label")
                    o = 2 * W - 0.15 * W
                    fill(g, (box[0] + o, box[1] + o, box[2] - o, box[3] - o), W, H, infill,
                         k % 2 == 0, W / 0.2, "infill")
            else:
                first_slab = local - (LEVEL - SLAB) <= H + 1e-6
                if first_slab:
                    g.fan(m["bridge_fan"])
                perimeters(g, slab_box, W, H, 30 if first_slab else outer, 30 if first_slab else inner, kind="slab")
                o = 2 * W - 0.15 * W
                fill(g, (slab_box[0] + o, slab_box[1] + o, slab_box[2] - o, slab_box[3] - o), W, H,
                     30 if first_slab else infill, first_slab or k % 2 == 0, W, "bridge" if first_slab else "slab")
                if first_slab and n >= m["fan_off_layers"]:
                    g.fan(m["fan"])
            # слой быстрее минимального времени - замедлить, как слайсер
            dt = g.time - t0
            if 0 < dt < m["min_layer_time"]:
                k_slow = dt / m["min_layer_time"]
                for i in range(layer_start, len(g.lines)):
                    s = g.lines[i]
                    if s.startswith("G1 X") and " E" in s and " F" in s:
                        head, f = s.rsplit(" F", 1)
                        g.lines[i] = f"{head} F{max(600, float(f) * k_slow):.0f}"
                g.time = t0 + m["min_layer_time"]
            n += 1
    end_gcode(g, max_z)
    grams = footer(g, title)
    name = f"ECC_0.4_TempTower_{mat_name}_{temps[0]}-{temps[-1]}.gcode"
    return g, name, grams, max_z


# ---------- линии опережения ----------

def pa_lines(mat_name):
    m = MATERIALS[mat_name]
    g = Gcode(m)
    H = 0.2
    W = 0.5
    values = [round(i * 0.005, 3) for i in range(17)]
    x_start, slow_len, fast_len = 60.0, 20.0, 40.0
    y0, step = 60.0, 5.0
    total = 2
    title = f"Линии опережения {mat_name} {values[0]:.3f}-{values[-1]:.3f}"
    start_gcode(g, m["first_temp"], title, total, 2 * H)
    fast = min(150.0, m["mvs"] * 0.9 / area(W, H))
    slow = 20.0

    g.layer(0, H, H, total)
    g.out(f"M104 S{m['first_temp']}")
    # рамка-якорь вокруг поля
    frame = (x_start - 6, y0 - 6, x_start + 2 * slow_len + fast_len + 24, y0 + step * (len(values) - 1) + 6)
    perimeters(g, frame, W, H, 30, 30, n=2, kind="base")
    x_end = x_start + 2 * slow_len + fast_len
    for i, v in enumerate(values):
        y = y0 + i * step
        g.retract()
        g.travel(x_start, y)
        g.out(f"SET_PRESSURE_ADVANCE ADVANCE={v:.3f}")
        g.out("M400")
        g.extrude(x_start + slow_len, y, W, H, slow, "slow", flow=1.0)
        g.extrude(x_start + slow_len + fast_len, y, W, H, fast, "fast", flow=1.0)
        g.extrude(x_end, y, W, H, slow, "slow", flow=1.0)
    g.out(f"SET_PRESSURE_ADVANCE ADVANCE={m['pa_default']:.3f} ; подписи - с обычным значением")
    for layer in (0, 1):
        if layer == 1:
            g.layer(1, 2 * H, H, total)
        for i, v in enumerate(values):
            y = y0 + i * step - 1.6
            txt = f"{round(v * 1000):03d}"
            for j, ch in enumerate(txt):
                for a, b in flat_digit_strokes(ch, x_end + 5 + j * 3.2, y):
                    g.travel(*a, hop=False) if math.hypot(a[0] - g.x, a[1] - g.y) <= 2 else g.travel(*a)
                    g.extrude(b[0], b[1], 0.4, H, 20, "label")
    end_gcode(g, 2 * H)
    grams = footer(g, title)
    name = f"ECC_0.4_PressureAdvance_Lines_{mat_name}_0-0.080.gcode"
    return g, name, grams, 2 * H


# ---------- общее для остальных тестов ----------

W, H = 0.45, 0.2   # линия и слой
W1 = 0.5           # линия первого слоя


def slow_layer(g, start, t0, min_time):
    """Слой быстрее минимального времени - замедлить печать, как делает слайсер."""
    dt = g.time - t0
    if 0 < dt < min_time:
        k = dt / min_time
        for i in range(start, len(g.lines)):
            s = g.lines[i]
            if s.startswith("G1 X") and " E" in s and " F" in s:
                head, f = s.rsplit(" F", 1)
                g.lines[i] = f"{head} F{max(600, float(f) * k):.0f}"
        g.time = t0 + min_time


def run_layers(g, zs, body, min_time=True):
    """Печать по слоям: zs - высоты слоёв, body(n, z, h) печатает слой n."""
    total = len(zs)
    prev = 0.0
    for n, z in enumerate(zs):
        h = z - prev
        g.layer(n, z, h, total)
        if n == g.mat["fan_off_layers"]:
            g.fan(g.mat["fan"])
        start, t0 = len(g.lines), g.time
        body(n, z, h)
        if min_time:
            slow_layer(g, start, t0, g.mat["min_layer_time"])
        prev = z


def layers_to(top, h=H):
    n = round(top / h)
    return [round(h * (i + 1), 3) for i in range(n)]


def inset(box, d):
    return (box[0] + d, box[1] + d, box[2] - d, box[3] - d)


def solid(g, box, n, w=W, h=H, walls=2, wall_speed=60, fill_speed=100, flow=None, along_x=None, kind="wall"):
    """Сплошной слой прямоугольника: стенки и заполнение 100 %."""
    perimeters(g, box, w, h, wall_speed, wall_speed * 1.5, n=walls, kind=kind)
    fill(g, inset(box, walls * w - 0.15 * w), w, h, fill_speed,
         (n % 2 == 0) if along_x is None else along_x, w, "infill", flow)


def sparse(g, box, n, w=W, h=H, walls=2, wall_speed=60, fill_speed=120, density=0.2, kind="wall"):
    perimeters(g, box, w, h, wall_speed, wall_speed * 1.5, n=walls, kind=kind)
    fill(g, inset(box, walls * w - 0.15 * w), w, h, fill_speed, n % 2 == 0, w / density, "infill")


def emboss(g, text, x0, y_face, v, W_=3.6, H_=6.0, S_=1.2, gap=1.0, w=W, h=H):
    """Выпуклая надпись на передней грани (y_face, наружу - меньший Y); v - высота от низа строки."""
    if not 0 <= v <= H_:
        return
    for a, b in text_intervals(text, x0, v, W_, H_, S_, gap):
        for yy in (y_face - 0.6, y_face - 0.15):
            xa, xb = a + w / 2, b - w / 2
            if xb - xa < 0.1:
                xa, xb = (a + b) / 2 - 0.05, (a + b) / 2 + 0.05
            g.travel(xa, yy, hop=False)
            g.extrude(xb, yy, w, h, 20, "label")


def flat_text(g, text, x0, y0, h, Wd=2.0, Hd=3.2, gap=1.2):
    """Надпись на столе: сегмент - одна линия."""
    for j, ch in enumerate(text):
        for a, b in flat_digit_strokes(ch, x0 + j * (Wd + gap), y0, Wd, Hd):
            if math.hypot(a[0] - g.x, a[1] - g.y) <= 2:
                g.travel(*a, hop=False)
            else:
                g.travel(*a)
            g.extrude(b[0], b[1], 0.4, h, 20, "label")


def text_width(text, Wd, gap):
    return len(text) * Wd + (len(text) - 1) * gap


def finish(g, name, title, max_z):
    end_gcode(g, max_z)
    grams = footer(g, title)
    return g, name, grams, max_z


# ---------- поток ----------

def flow_test(mat_name):
    """9 плашек 22x22 мм с потоком 80-120 % от профиля. Лучшая - самая гладкая верхняя
    поверхность без щелей между линиями и без бугров."""
    m = MATERIALS[mat_name]
    g = Gcode(m)
    pcts = [80, 85, 90, 95, 100, 105, 110, 115, 120]
    boxes = []
    for i, p in enumerate(pcts):
        cx = 94 + (i % 3) * 34
        cy = 167 - (i // 3) * 36
        boxes.append(((cx - 11, cy - 11, cx + 11, cy + 11), p))
    zs = layers_to(1.2)
    title = f"Поток {mat_name} 80-120 %"
    start_gcode(g, m["first_temp"], title, len(zs), zs[-1])

    def body(n, z, h):
        w = W1 if n == 0 else W
        for box, p in boxes:
            flow = m["flow"] * p / 100
            perimeters(g, box, w, h, 40 if n == 0 else 60, 40 if n == 0 else 90, n=2)
            fill(g, inset(box, 2 * w - 0.15 * w), w, h, 40 if n == 0 else 80,
                 n % 2 == 0 or n == len(zs) - 1, w, "top" if n == len(zs) - 1 else "infill", flow)
            if n < 2:
                txt = str(p)
                flat_text(g, txt, (box[0] + box[2]) / 2 - text_width(txt, 2.0, 1.2) / 2, box[1] - 6, h)

    run_layers(g, zs, body)
    return finish(g, f"ECC_0.4_Flow_{mat_name}_80-120.gcode", title, zs[-1])


# ---------- откат ----------

def retraction_test(mat_name):
    """Две колонны 12x8 мм в 40 мм друг от друга; длина отката растёт по уровням 5 мм:
    0.2 ... 1.6 мм. Лучший уровень - наименьший откат без нитей между колоннами."""
    m = MATERIALS[mat_name]
    g = Gcode(m)
    values = [0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6]
    LEVEL, BASE = 5.0, 0.6
    A = (96.0, 124.0, 108.0, 132.0)
    B = (148.0, 124.0, 160.0, 132.0)
    base_box = (92.0, 120.0, 164.0, 136.0)
    zs = layers_to(BASE + LEVEL * len(values))
    title = f"Откат {mat_name} 0.2-1.6 мм"
    start_gcode(g, m["first_temp"], title, len(zs), zs[-1])

    def body(n, z, h):
        if z <= BASE + 1e-6:
            solid(g, base_box, n, w=W1 if n == 0 else W, h=h, wall_speed=40)
            return
        lvl = min(int((z - BASE - 1e-6) / LEVEL), len(values) - 1)
        if g.retract_len != values[lvl]:
            g.out(f"; ===== уровень {lvl + 1}: откат {values[lvl]} мм =====")
            g.retract_len = values[lvl]
        local = z - BASE - lvl * LEVEL
        for box in (A, B):
            sparse(g, box, n, h=h)
            if box is A:
                txt = f"{round(values[lvl] * 10):02d}"
                emboss(g, txt, A[0] + (12 - text_width(txt, 2.6, 0.8)) / 2, A[1], local - h / 2 - 0.7,
                       W_=2.6, H_=3.6, S_=0.9, gap=0.8)

    run_layers(g, zs, body)
    return finish(g, f"ECC_0.4_Retraction_{mat_name}_0.2-1.6.gcode", title, zs[-1])


# ---------- максимальный расход ----------

def max_flow_test(mat_name):
    """Коробка в одну стенку 0.6 мм, слой 0.3; скорость растёт с высотой: на каждый мм +1 мм3/с.
    Где стенка стала рваной или экструдер защёлкал - предел; цифры на передней стенке -
    мм3/с на этой высоте. В профиль брать ~80-90 % от предела."""
    m = MATERIALS[mat_name]
    g = Gcode(m)
    v0 = 4.0 if mat_name == "PETG" else 8.0
    v1 = 28.0 if mat_name == "PETG" else 40.0
    box = (78.0, 118.0, 178.0, 138.0)
    WW, HH = 0.6, 0.3
    BASE = 0.4
    zs = [0.2, 0.4] + [round(BASE + HH * (i + 1), 3) for i in range(round((v1 - v0) / HH))]
    title = f"Максимальный расход {mat_name} {v0:.0f}-{v1:.0f} мм3/с"
    start_gcode(g, m["first_temp"], title, len(zs), zs[-1])
    g.out("SET_VELOCITY_LIMIT ACCEL=10000")

    def body(n, z, h):
        if z <= BASE + 1e-6:
            solid(g, box, n, w=W1, h=h, wall_speed=40, fill_speed=60)
            return
        vol = v0 + (z - BASE)
        speed = vol / area(WW, HH)
        o = WW / 2
        loop = [(box[0] + o, box[1] + o), (box[2] - o, box[1] + o), (box[2] - o, box[3] - o), (box[0] + o, box[3] - o)]
        g.travel(*loop[0])
        for p in loop[1:] + loop[:1]:
            g.extrude(p[0], p[1], WW, HH, speed, "wall", flow=1.0, cap=False)
        # подписи через каждые 4 мм3/с: цифры 3 мм высотой, начало строки - на своей высоте
        for mark in range(int(v0) + 4, int(v1), 4):
            v = (z - BASE) - (mark - v0) - HH / 2
            if 0 <= v <= 3.0:
                emboss(g, str(mark), box[0] + 4, box[1], v, W_=2.2, H_=3.0, S_=0.8, gap=0.7, h=HH)

    run_layers(g, zs, body, min_time=False)
    return finish(g, f"ECC_0.4_MaxFlow_{mat_name}_{v0:.0f}-{v1:.0f}.gcode", title, zs[-1])


# ---------- нависания и мосты ----------

def overhang_bridge_test(mat_name):
    """Сзади - стенка с 7 «плавниками», нависающими вперёд под 20-80° от вертикали; спереди -
    5 мостов 10-50 мм между столбиками. Подписи на столе перед каждым."""
    m = MATERIALS[mat_name]
    g = Gcode(m)
    angles = [20, 30, 40, 50, 60, 70, 80]
    spine = (60.0, 170.0, 134.0, 176.0)
    spine_base = (58.0, 168.0, 136.0, 178.0)
    fin_z0, top_ov = 1.0, 16.0
    lengths = [10, 20, 30, 40, 50]
    rows = [(60.0 + 0, 60.0 + i * 18) for i in range(len(lengths))]
    PILLAR_H, SLAB = 8.0, 1.0
    zs = layers_to(top_ov)
    title = f"Нависания 20-80° и мосты 10-50 мм {mat_name}"
    start_gcode(g, m["first_temp"], title, len(zs), zs[-1])

    def body(n, z, h):
        w = W1 if n == 0 else W
        # нависания
        if z <= fin_z0 + 1e-6:
            solid(g, spine_base, n, w=w, h=h, wall_speed=40)
        else:
            sparse(g, spine, n, h=h)
            for i, a in enumerate(angles):
                d = min(12.0, (z - fin_z0) * math.tan(math.radians(a)))
                if d >= 1.0:
                    x = 62.0 + i * 10
                    solid(g, (x, spine[1] - d, x + 8, spine[1] + 0.5), n, h=h, wall_speed=40, fill_speed=60)
        if n < 2:
            for i, a in enumerate(angles):
                flat_text(g, str(a), 62.0 + i * 10 + 4 - text_width(str(a), 2.0, 1.2) / 2, spine[1] - 18, h)
        # мосты
        for (x0, y0), L in zip(rows, lengths):
            left = (x0, y0, x0 + 6, y0 + 8)
            right = (x0 + 6 + L, y0, x0 + 12 + L, y0 + 8)
            if z <= PILLAR_H + 1e-6:
                for p in (left, right):
                    solid(g, p, n, w=w, h=h, wall_speed=40 if n == 0 else 60)
            elif z <= PILLAR_H + SLAB + 1e-6:
                first = z - PILLAR_H <= h + 1e-6
                if first:
                    g.fan(m["bridge_fan"])
                slab = (x0, y0, x0 + 12 + L, y0 + 8)
                solid(g, slab, n, h=h, wall_speed=30 if first else 60, fill_speed=30 if first else 80,
                      along_x=True if first else None, kind="bridge" if first else "slab")
                if first and n >= m["fan_off_layers"]:
                    g.fan(m["fan"])
            if n < 2:
                flat_text(g, str(L), x0 + 12 + L + 4, y0 + 2.4, h)

    run_layers(g, zs, body)
    return finish(g, f"ECC_0.4_OverhangBridge_{mat_name}.gcode", title, zs[-1])


# ---------- первый слой ----------

def first_layer_test(mat_name):
    """9 квадратов 34x34 мм в один слой по всему столу. Везде одинаково гладко, без щелей и
    без «борозд» - стол и высота первого слоя в порядке."""
    m = MATERIALS[mat_name]
    g = Gcode(m)
    zs = [0.2]
    title = f"Первый слой {mat_name}"
    start_gcode(g, m["first_temp"], title, 1, 0.2)
    centers = [34.0, 128.0, 222.0]

    def body(n, z, h):
        for cy in centers:
            for cx in (centers if cy != 34.0 else centers[::-1]):
                solid(g, (cx - 17, cy - 17, cx + 17, cy + 17), 0, w=W1, h=h, wall_speed=40, fill_speed=50)

    run_layers(g, zs, body, min_time=False)
    return finish(g, f"ECC_0.4_FirstLayer_{mat_name}.gcode", title, 0.2)


# ---------- зазоры ----------

def tolerance_test(mat_name):
    """6 рамок со штырём внутри, зазор 0.10-0.40 мм. После печати провернуть/выдавить штыри:
    наименьший зазор, где штырь свободно выходит, - зазор для подвижных деталей."""
    m = MATERIALS[mat_name]
    g = Gcode(m)
    gaps = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40]
    PEG = 8.0
    zs = layers_to(6.0)
    title = f"Зазоры {mat_name} 0.10-0.40 мм"
    start_gcode(g, m["first_temp"], title, len(zs), zs[-1])

    def body(n, z, h):
        w = W  # и первый слой той же ширины: широкий первый слой залил бы узкие зазоры
        sp = 30 if n == 0 else 60
        for i, gap in enumerate(gaps):
            cx, cy = 73.0 + i * 22, 128.0
            outer = (cx - 9, cy - 9, cx + 9, cy + 9)
            hole = (cx - PEG / 2 - gap, cy - PEG / 2 - gap, cx + PEG / 2 + gap, cy + PEG / 2 + gap)
            peg = (cx - PEG / 2, cy - PEG / 2, cx + PEG / 2, cy + PEG / 2)
            # рамка: наружные стенки, стенки отверстия (изнутри наружу), заполнение четырёх полос
            perimeters(g, outer, w, h, sp, sp * 1.5, n=2)
            for k in range(2):
                o = w / 2 + k * w
                g.path(rect_loop(hole[0] - o, hole[1] - o, hole[2] + o, hole[3] + o), w, h, sp, "wall" if k == 0 else "inner", closed=True)
            a, b = inset(outer, 2 * w - 0.15 * w), inset(hole, -(2 * w - 0.15 * w))
            for strip in ((a[0], a[1], a[2], b[1]), (a[0], b[3], a[2], a[3]), (a[0], b[1], b[0], b[3]), (b[2], b[1], a[2], b[3])):
                if strip[2] - strip[0] > w and strip[3] - strip[1] > w:
                    fill(g, strip, w, h, sp, n % 2 == 0, w, "infill")
            solid(g, peg, n, w=w, h=h, wall_speed=sp, fill_speed=sp)
            if n < 2:
                txt = f"{round(gap * 100):02d}"
                flat_text(g, txt, cx - text_width(txt, 2.0, 1.2) / 2, outer[1] - 6, h)

    run_layers(g, zs, body)
    return finish(g, f"ECC_0.4_Tolerance_{mat_name}_0.10-0.40.gcode", title, zs[-1])


# ---------- размеры ----------

def cube_test(mat_name):
    """Кубик 20x20x20 мм: 3 стенки, 20 % заполнения, 4 нижних и 5 верхних сплошных слоёв.
    Штангенциркулем: X - слева направо, Y - спереди назад (передняя грань - с подписью «20»),
    Z - высота. Все стороны меньше или больше 20 одинаково - поток (тест потока) или усадка
    пластика; разница только по X или только по Y - натяжение ремня этой оси; отверстия и
    подвижные детали - по тесту зазоров."""
    m = MATERIALS[mat_name]
    g = Gcode(m)
    box = (118.0, 118.0, 138.0, 138.0)
    zs = layers_to(20.0)
    title = f"Кубик 20 мм {mat_name}"
    start_gcode(g, m["first_temp"], title, len(zs), zs[-1])

    def body(n, z, h):
        w = W1 if n == 0 else W
        if n < 4 or n >= len(zs) - 5:
            solid(g, box, n, w=w, h=h, walls=3, wall_speed=40 if n == 0 else 60)
        else:
            sparse(g, box, n, h=h, walls=3)
        emboss(g, "20", box[0] + (20 - text_width("20", 3.6, 1.0)) / 2, box[1], z - h / 2 - 7.0)

    run_layers(g, zs, body)
    return finish(g, f"ECC_0.4_Cube20_{mat_name}.gcode", title, zs[-1])


# ---------- волны после углов ----------

def ringing_test(mat_name):
    """Коробка 60x60 в две стенки, 12 поясов по 5 мм; разгон растёт по поясам 1000-12000 мм/с2
    (цифры на передней стенке - тысячи). Смотреть рябь на стенках сразу после углов:
    с какого пояса она появилась - это предел разгона для наружных стенок."""
    m = MATERIALS[mat_name]
    g = Gcode(m)
    box = (98.0, 98.0, 158.0, 158.0)
    BAND, BASE = 5.0, 0.6
    accels = [1000 * (i + 1) for i in range(12)]
    speed = min(150.0, m["mvs"] * 0.9 / area(W, H))
    zs = layers_to(BASE + BAND * len(accels))
    title = f"Волны после углов {mat_name}, разгон 1000-12000"
    start_gcode(g, m["first_temp"], title, len(zs), zs[-1])

    def body(n, z, h):
        if z <= BASE + 1e-6:
            solid(g, box, n, w=W1 if n == 0 else W, h=h, wall_speed=40)
            return
        band = min(int((z - BASE - 1e-6) / BAND), len(accels) - 1)
        local = z - BASE - band * BAND
        if local <= h + 1e-6:
            g.out(f"; ===== пояс {band + 1}: разгон {accels[band]} =====")
            g.out(f"SET_VELOCITY_LIMIT ACCEL={accels[band]}")
            g.out(f"M204 S{accels[band]}")
        perimeters(g, box, W, h, speed, speed, n=2)
        emboss(g, str(band + 1), box[0] + 6, box[1], local - h / 2 - 0.7, W_=2.6, H_=3.6, S_=0.9, gap=0.8)

    run_layers(g, zs, body, min_time=False)
    return finish(g, f"ECC_0.4_Ringing_{mat_name}_1k-12k.gcode", title, zs[-1])


# ---------- проверки и картинки ----------

def check(g, name, max_z):
    xs = [c for s in g.segments for c in (s[0], s[2])]
    ys = [c for s in g.segments for c in (s[1], s[3])]
    assert min(xs) >= 0 and max(xs) <= BED, f"{name}: X вне стола {min(xs)}..{max(xs)}"
    assert min(ys) >= 0 and max(ys) <= BED, f"{name}: Y вне стола {min(ys)}..{max(ys)}"
    assert max(s[4] for s in g.segments) <= max_z + 1e-6, f"{name}: Z выше расчётного"
    for l in g.lines:
        if l.startswith("G1") and " F" in l:
            f = float(l.rsplit(" F", 1)[1].split()[0])
            assert 300 <= f <= 20000, f"{name}: скорость {f}"
    return min(xs), max(xs), min(ys), max(ys)


def preview(g, name):
    from PIL import Image, ImageDraw
    colors = {"top": (250, 250, 250), "wall": (235, 120, 40), "inner": (200, 170, 60), "infill": (120, 120, 120), "slab": (90, 140, 220),
              "bridge": (40, 90, 255), "base": (150, 150, 150), "label": (255, 40, 40), "slow": (60, 180, 90),
              "fast": (230, 60, 160)}
    PREVIEW.mkdir(exist_ok=True)
    sc = 8
    top = Image.new("RGB", (int(BED * sc / 2), int(BED * sc / 2)), (28, 30, 36))
    d = ImageDraw.Draw(top)
    zmin = min(s[4] for s in g.segments)
    for x1, y1, x2, y2, z, k in g.segments:
        if z <= zmin + 0.21 or k == "label":
            d.line([(x1 * sc / 2, (BED - y1) * sc / 2), (x2 * sc / 2, (BED - y2) * sc / 2)], fill=colors.get(k, (255, 255, 255)), width=2)
    top.save(PREVIEW / (name.replace(".gcode", "") + "_top.png"))
    # вид спереди (X-Z) для башни
    if max(s[4] for s in g.segments) > 2 and any(s[4] > 1.0 for s in g.segments):
        xs = [c for s in g.segments for c in (s[0], s[2])]
        x0, x1 = min(xs) - 5, max(xs) + 5
        zs = max(s[4] for s in g.segments) + 5
        sc2 = 10
        fr = Image.new("RGB", (int((x1 - x0) * sc2), int(zs * sc2)), (28, 30, 36))
        d = ImageDraw.Draw(fr)
        # передняя грань: сначала всё, потом подписи поверх
        y_front = min(min(s[1], s[3]) for s in g.segments if s[5] != "label" and s[4] > 1.0)
        for x1_, y1_, x2_, y2_, z, k in sorted(g.segments, key=lambda s: s[5] == "label"):
            if min(y1_, y2_) < y_front + 1.5 or k == "label":
                d.line([((x1_ - x0) * sc2, (zs - z) * sc2), ((x2_ - x0) * sc2, (zs - z) * sc2)],
                       fill=colors.get(k, (255, 255, 255)), width=2)
        fr.save(PREVIEW / (name.replace(".gcode", "") + "_front.png"))


def main():
    do_preview = "--preview" in sys.argv
    for build in (temp_tower, pa_lines, flow_test, retraction_test, max_flow_test, overhang_bridge_test,
                  first_layer_test, tolerance_test, cube_test, ringing_test):
        for mat in MATERIALS:
            g, name, grams, max_z = build(mat)
            box = check(g, name, max_z)
            target = OUT / name
            target.write_text("\n".join(g.lines) + "\n", encoding="utf-8", newline="\n")
            h, mnt = divmod(round(g.time / 60), 60)
            print(f"{name}: {len(g.lines)} строк, ~{h}ч {mnt}м, ~{grams:.0f} г, поле X {box[0]:.0f}-{box[1]:.0f} Y {box[2]:.0f}-{box[3]:.0f}")
            if do_preview:
                preview(g, name)


if __name__ == "__main__":
    main()
