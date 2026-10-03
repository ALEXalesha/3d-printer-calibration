"""The G-code generator: reference/calibration.py with its globals moved into a context.

Structure and names follow the reference line by line on purpose: the golden test checks
that the Elegoo Centauri Carbon profile still gives the very same bytes, and the
JavaScript twin (web/js/core/generator.js) is a translation of this file. Anything that
touches a number on its way into the file goes through num.py.

What changed against the reference:
- bed, nozzle, filament, retraction, speeds, acceleration, start and end code and the
  firmware commands come from the printer profile and the firmware table;
- test sizes scale with the nozzle (line width, layer height), ranges come from params;
- the whole layout is shifted to the bed centre (zero shift for a 256 mm bed);
- comments can be Russian (the reference) or English.
"""
import json
import math

from . import num, profiles, templates
from .num import fixed, hypot, py_repr, py_round, sq, trim

_TEXT = None


def text(key, lang, **values):
    global _TEXT
    if _TEXT is None:
        _TEXT = json.loads((profiles.profiles_dir() / "gcode_text.json").read_text(encoding="utf-8"))
    s = _TEXT[key]["en" if lang == "en" else "ru"]
    for k, v in values.items():
        s = s.replace("{" + k + "}", v)
    return s


class TemplateError(ValueError):
    def __init__(self, names):
        super().__init__("unknown placeholders: " + ", ".join("{" + n + "}" for n in names))
        self.names = names


class DoesNotFit(ValueError):
    pass


def firmware_commands(printer):
    fw = profiles.firmware()[printer["firmware"]]
    out = {k: fw[k] for k in ("pressure_advance", "accel", "accel_band", "layer_progress", "fan")}
    for k, v in (printer.get("fw_overrides") or {}).items():
        if k in out:
            out[k] = v
    return out


def area(w, h):
    """Сечение валика: прямоугольник со скруглёнными краями, как считает слайсер."""
    return (w - h) * h + math.pi * sq(h / 2)


class Ctx:
    """Everything the reference kept in module constants."""

    def __init__(self, printer, material, lang="ru", shift=(0.0, 0.0)):
        self.p = printer
        self.m = material
        self.lang = lang
        self.fw = firmware_commands(printer)
        n = printer["nozzle"]
        self.NOZ = n
        self.W = py_round(1.125 * n, 3)     # 0.45 for a 0.4 nozzle
        self.W1 = py_round(1.25 * n, 3)     # 0.5  - first layer
        self.H = py_round(0.5 * n, 3)       # 0.2  - layer
        self.LW = n                         # 0.4  - lines of digits on the bed
        self.WW = py_round(1.5 * n, 3)      # 0.6  - max flow wall
        self.HH = py_round(0.75 * n, 3)     # 0.3  - max flow layer
        self.FIL_AREA = math.pi * sq(printer["filament_diameter"] / 2)
        r = printer["retract"]
        self.RETRACT = r["length"]
        self.RETRACT_F = r["speed"] * 60
        self.ZHOP = r["z_hop"]
        self.TRAVEL_F = printer["travel_speed"] * 60
        self.Z_F = printer["z_speed"] * 60
        self.MAX_SPEED = printer["max_speed"]
        bed = printer["bed"]
        # The layout is drawn for a 256 mm bed with its centre at 128, 128 (the reference).
        if bed["origin"] == "center":
            self.ox, self.oy = -128.0 + shift[0], -128.0 + shift[1]
        else:
            self.ox, self.oy = bed["x"] / 2 - 128 + shift[0], bed["y"] / 2 - 128 + shift[1]

    # frame <-> printer coordinates
    def px(self, x):
        return x + self.ox

    def py(self, y):
        return y + self.oy


class Gcode:
    def __init__(self, ctx):
        self.ctx = ctx
        self.mat = ctx.m
        self.lines = []
        self.x = self.y = 0.0
        self.z = 0.0
        self.retracted = False
        self.segments = []  # (x1, y1, x2, y2, z, kind) - frame coordinates
        self.time = 0.0
        self.e_total = 0.0
        self.retract_len = ctx.RETRACT
        self.body_start = 0
        self.body_end = None

    def out(self, s):
        self.lines.append(s)

    def retract(self):
        if not self.retracted and self.retract_len > 0:
            c = self.ctx
            self.out(f"G1 E-{fixed(self.retract_len, 2)} F{fixed(c.RETRACT_F, 0)}")
            self.time += self.retract_len / (c.RETRACT_F / 60)
            self.retracted = self.retract_len

    def unretract(self):
        if self.retracted:
            c = self.ctx
            self.out(f"G1 E{fixed(self.retracted, 2)} F{fixed(c.RETRACT_F, 0)}")  # вернуть ровно столько, сколько втянули
            self.time += self.retracted / (c.RETRACT_F / 60)
            self.retracted = False

    def travel(self, x, y, hop=True):
        c = self.ctx
        d = hypot(x - self.x, y - self.y)
        if d < 0.01:
            return
        long_move = d > 2.0
        if long_move:
            self.retract()
            if hop and c.ZHOP > 0:
                self.out(f"G1 Z{fixed(self.z + c.ZHOP, 3)} F{fixed(c.Z_F, 0)}")
        self.out(f"G1 X{fixed(c.px(x), 3)} Y{fixed(c.py(y), 3)} F{fixed(c.TRAVEL_F, 0)}")
        if long_move and hop and c.ZHOP > 0:
            self.out(f"G1 Z{fixed(self.z, 3)} F{fixed(c.Z_F, 0)}")
        self.time += d / (c.TRAVEL_F / 60) + (0.1 if long_move else 0)
        self.x, self.y = x, y

    def extrude(self, x, y, w, h, speed, kind, flow=None, cap=True):
        c = self.ctx
        d = hypot(x - self.x, y - self.y)
        if d < 0.01:
            return
        self.unretract()
        e = d * area(w, h) / c.FIL_AREA * (flow if flow is not None else self.mat["flow"])
        if cap:
            speed = min(speed, self.mat["mvs"] * 0.9 / area(w, h))  # не выше расхода пластика
        if speed > c.MAX_SPEED:
            speed = c.MAX_SPEED
        self.out(f"G1 X{fixed(c.px(x), 3)} Y{fixed(c.py(y), 3)} E{fixed(e, 5)} F{fixed(speed * 60, 0)}")
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
        self.out(self.ctx.fw["fan"].replace("{s255}", str(py_round(255 * frac))).replace("{s1}", fixed(frac, 2)))

    def layer(self, n, z, h, total):
        c = self.ctx
        self.out(";LAYER_CHANGE")
        self.out(f";Z:{fixed(z, 2)}")
        self.out(f";HEIGHT:{fixed(h, 2)}")
        self.out(f";LAYER:{n}")
        self.retract()
        self.out(f"G1 Z{fixed(z, 3)} F{fixed(c.Z_F, 0)}")
        if c.fw["layer_progress"]:
            self.out(c.fw["layer_progress"].replace("{total}", str(total)).replace("{n}", str(n + 1)))
        self.z = z
        if n == 1 and self.mat["nozzle_temp"] != self.mat["first_layer_temp"] and not getattr(self, "fixed_temp", False):
            self.out(f"M104 S{self.mat['nozzle_temp']}" + text("first_layer_temp_switch", c.lang))

    def accel(self, a, band=False):
        for s in self.ctx.fw["accel_band" if band else "accel"]:
            self.out(s.replace("{a}", str(a)))

    def pressure_advance(self, v, comment=""):
        self.out(self.ctx.fw["pressure_advance"].replace("{v}", fixed(v, 3)) + comment)


# ---------- начало и конец - из профиля принтера ----------

def purge_geometry(ctx):
    """Two purge lines at the front-left edge of the bed (printer coordinates)."""
    bed = ctx.p["bed"]
    if bed["shape"] == "round":
        r = min(bed["x"], bed["y"]) / 2
        y0 = -(r - 8)
        half = min(50.0, math.sqrt(r * r - y0 * y0) - 5)
        a, b = (-half, y0), (half, y0)
        c, d = (half, y0 + 1.0), (-half, y0 + 1.0)
    else:
        x0 = -bed["x"] / 2 if bed["origin"] == "center" else 0.0
        y0 = -bed["y"] / 2 if bed["origin"] == "center" else 0.0
        length = min(100.0, bed["y"] - 40)
        a, b = (x0 + 3, y0 + 20), (x0 + 3, y0 + 20 + length)
        c, d = (x0 + 4, y0 + 20 + length), (x0 + 4, y0 + 20)
    length = hypot(b[0] - a[0], b[1] - a[1])
    e = length * area(2 * ctx.NOZ, 0.3) / ctx.FIL_AREA
    return a, b, c, d, e


def template_values(ctx, first_temp, title, total_layers, max_z):
    p, m = ctx.p, ctx.m
    mvs = m["mvs"]
    f1 = min(6000, max(900, mvs / 0.5 / 0.3 * 60))
    f2 = min(12000, max(1200, mvs / 0.5 / 0.3 * 60))
    bed_z = p["bed"]["z"]
    if max_z > 100:
        capped = fixed(min(max_z + 50, bed_z + 0.5), 2)
    elif bed_z < 100:
        capped = fixed(min(max_z + 10, bed_z), 2)
    else:
        capped = "100"
    a, b, c, d, e = purge_geometry(ctx)
    v = {
        "nozzle_temp": str(m["nozzle_temp"]),
        "first_layer_nozzle_temp": str(first_temp),
        "bed_temp": str(m["bed"]),
        "max_z": fixed(max_z, 2),
        "max_z_plus_half": fixed(max_z + 0.5, 2),
        "max_z_plus_50_capped": capped,
        "park_z": fixed(min(max_z + 10, bed_z), 2),
        "filament_type": m["type"],
        "layer_height": fixed(ctx.H, 2),
        "print_title": title,
        "total_layers": str(total_layers),
        "accel": str(p["default_accel"]),
        "set_accel": "\n".join(s.replace("{a}", str(p["default_accel"])) for s in ctx.fw["accel"]),
        "purge_f1": fixed(f1, 0),
        "purge_f2": fixed(f2, 0),
        "purge_f2_slow": fixed(0.2 * f2, 0),
        "travel_f": fixed(ctx.TRAVEL_F, 0),
        "z_f": fixed(ctx.Z_F, 0),
        "retract_len": fixed(ctx.RETRACT, 2),
        "retract_f": fixed(ctx.RETRACT_F, 0),
        "bed_x": trim(p["bed"]["x"], 2),
        "bed_y": trim(p["bed"]["y"], 2),
        "purge_x0": fixed(a[0], 2), "purge_y0": fixed(a[1], 2),
        "purge_x1": fixed(b[0], 2), "purge_y1": fixed(b[1], 2),
        "purge_x2": fixed(c[0], 2), "purge_y2": fixed(c[1], 2),
        "purge_x3": fixed(d[0], 2), "purge_y3": fixed(d[1], 2),
        "purge_e": fixed(e, 3),
        "park_x": fixed((-p["bed"]["x"] / 2 + 5) if p["bed"]["origin"] == "center" else 5.0, 2),
        "park_y": fixed((p["bed"]["y"] / 2 - 5) if p["bed"]["origin"] == "center" else p["bed"]["y"] - 5, 2),
    }
    flags = dict(p.get("options") or {})
    flags["pla_hot_bed"] = m["type"] == "PLA" and m["bed"] > 50
    return v, flags


def expand_template(ctx, lines, values, flags):
    out, unknown = templates.expand(lines, values, flags)
    if unknown:
        raise TemplateError(unknown)
    return out


def start_gcode(g, first_temp, title, total_layers, max_z):
    ctx = g.ctx
    values, flags = template_values(ctx, first_temp, title, total_layers, max_z)
    g.out("; HEADER_BLOCK_START")
    g.out(text("generated_by", ctx.lang, version=profiles.version(), title=title))
    g.out(f"; total layer number: {total_layers}")
    g.out(f"; filament_diameter: {trim(ctx.p['filament_diameter'], 3)}")
    g.out(f"; max_z_height: {fixed(max_z, 2)}")
    g.out("; HEADER_BLOCK_END")
    g.out("")
    g.out("; EXECUTABLE_BLOCK_START")
    body = expand_template(ctx, ctx.p["start_gcode"], values, flags)
    for s in body:
        g.out(s)
    st = ctx.p.get("start_state")
    if st is None:
        from .gcode_sim import end_state
        st = end_state(body)
    g.x, g.y, g.z = st["x"] - ctx.ox, st["y"] - ctx.oy, st["z"]
    g.time += st["time"]  # нагрев, парковка, чистка и прочистка - примерно
    g.e_total += st["e"]
    g.body_start = len(g.lines)


def end_gcode(g, max_z):
    ctx = g.ctx
    g.body_end = len(g.lines)
    values, flags = template_values(ctx, 0, "", 0, max_z)
    for s in expand_template(ctx, ctx.p["end_gcode"], values, flags):
        g.out(s)
    g.out("; EXECUTABLE_BLOCK_END")


def footer(g, title):
    grams = g.e_total * g.ctx.FIL_AREA / 1000 * g.mat["density"]
    h, m = divmod(py_round(g.time / 60), 60)
    g.out("")
    g.out(f"; {title}")
    g.out(f"; filament used [mm] = {fixed(g.e_total, 2)}")
    g.out(f"; filament used [g] = {fixed(grams, 2)}")
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
            g.extrude(a[0], a[1], w, h, speed, kind, flow)
        g.extrude(b[0], b[1], w, h, speed, kind, flow)


# ---------- цифры: семь сегментов ----------

SEGS = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd",
        "6": "afgedc", "7": "abc", "8": "abcdefg", "9": "abcdfg"}


def seg_boxes(W, H, S):
    return {"a": (0, W, H - S, H), "g": (0, W, (H - S) / 2, (H + S) / 2), "d": (0, W, 0, S),
            "f": (0, S, H / 2, H), "b": (W - S, W, H / 2, H), "e": (0, S, 0, H / 2), "c": (W - S, W, 0, H / 2)}


def text_intervals(txt, x0, v, W=3.6, H=6.0, S=1.2, gap=1.0):
    boxes = seg_boxes(W, H, S)
    out = []
    for i, ch in enumerate(txt):
        dx = x0 + i * (W + gap)
        spans = sorted((dx + b[0], dx + b[1]) for s in SEGS[ch] for b in [boxes[s]] if b[2] <= v <= b[3])
        for a, b in spans:  # слить перекрывающиеся
            if out and a <= out[-1][1] + 1e-6 and out[-1][0] >= dx - 1e-6:
                out[-1] = (out[-1][0], max(out[-1][1], b))
            else:
                out.append((a, b))
    return out


def flat_digit_strokes(ch, x0, y0, W=2.0, H=3.2):
    p = {"a": ((0, H), (W, H)), "g": ((0, H / 2), (W, H / 2)), "d": ((0, 0), (W, 0)),
         "f": ((0, H / 2), (0, H)), "b": ((W, H / 2), (W, H)), "e": ((0, 0), (0, H / 2)), "c": ((W, 0), (W, H / 2))}
    order = "fabgedc"
    return [((x0 + p[s][0][0], y0 + p[s][0][1]), (x0 + p[s][1][0], y0 + p[s][1][1])) for s in order if s in SEGS[ch]]


# ---------- общее для тестов ----------

def slow_layer(g, start, t0, min_time):
    """Слой быстрее минимального времени - замедлить печать, как делает слайсер."""
    dt = g.time - t0
    if 0 < dt < min_time:
        k = dt / min_time
        for i in range(start, len(g.lines)):
            s = g.lines[i]
            if s.startswith("G1 X") and " E" in s and " F" in s:
                head, f = s.rsplit(" F", 1)
                g.lines[i] = f"{head} F{fixed(max(600, float(f) * k), 0)}"
        g.time = t0 + min_time


def run_layers(g, zs, body, min_time=True):
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


def layers_to(top, h):
    n = py_round(top / h)
    return [py_round(h * (i + 1), 3) for i in range(n)]


def inset(box, d):
    return (box[0] + d, box[1] + d, box[2] - d, box[3] - d)


def solid(g, box, n, w=None, h=None, walls=2, wall_speed=60, fill_speed=100, flow=None, along_x=None, kind="wall"):
    w = g.ctx.W if w is None else w
    h = g.ctx.H if h is None else h
    perimeters(g, box, w, h, wall_speed, wall_speed * 1.5, n=walls, kind=kind)
    fill(g, inset(box, walls * w - 0.15 * w), w, h, fill_speed,
         (n % 2 == 0) if along_x is None else along_x, w, "infill", flow)


def sparse(g, box, n, w=None, h=None, walls=2, wall_speed=60, fill_speed=120, density=0.2, kind="wall"):
    w = g.ctx.W if w is None else w
    h = g.ctx.H if h is None else h
    perimeters(g, box, w, h, wall_speed, wall_speed * 1.5, n=walls, kind=kind)
    fill(g, inset(box, walls * w - 0.15 * w), w, h, fill_speed, n % 2 == 0, w / density, "infill")


def emboss(g, txt, x0, y_face, v, W_=3.6, H_=6.0, S_=1.2, gap=1.0, w=None, h=None):
    """Выпуклая надпись на передней грани (y_face, наружу - меньший Y); v - высота от низа строки."""
    w = g.ctx.W if w is None else w
    h = g.ctx.H if h is None else h
    if not 0 <= v <= H_:
        return
    for a, b in text_intervals(txt, x0, v, W_, H_, S_, gap):
        for yy in (y_face - 0.6, y_face - 0.15):
            xa, xb = a + w / 2, b - w / 2
            if xb - xa < 0.1:
                xa, xb = (a + b) / 2 - 0.05, (a + b) / 2 + 0.05
            g.travel(xa, yy, hop=False)
            g.extrude(xb, yy, w, h, 20, "label")


def flat_text(g, txt, x0, y0, h, Wd=2.0, Hd=3.2, gap=1.2):
    for j, ch in enumerate(txt):
        for a, b in flat_digit_strokes(ch, x0 + j * (Wd + gap), y0, Wd, Hd):
            if hypot(a[0] - g.x, a[1] - g.y) <= 2:
                g.travel(*a, hop=False)
            else:
                g.travel(*a)
            g.extrude(b[0], b[1], g.ctx.LW, h, 20, "label")


def text_width(txt, Wd, gap):
    return len(txt) * Wd + (len(txt) - 1) * gap


def file_name(ctx, test, mat_name, rng=""):
    return f"{ctx.p['prefix']}_{trim(ctx.NOZ, 2)}_{test}_{mat_name}{('_' + rng) if rng else ''}.gcode"


class Result:
    def __init__(self, g, name, title, grams, max_z):
        self.g = g
        self.name = name
        self.title = title
        self.grams = grams
        self.max_z = max_z

    @property
    def text(self):
        return "\n".join(self.g.lines) + "\n"

    @property
    def time(self):
        return self.g.time


def finish(g, name, title, max_z):
    end_gcode(g, max_z)
    grams = footer(g, title)
    return Result(g, name, title, grams, max_z)


# ---------- башня температур ----------

def temp_tower(ctx, prm):
    m = ctx.m
    g = Gcode(ctx)
    g.fixed_temp = True
    H = ctx.H
    W = ctx.W
    t0, t1, step = prm["t_start"], prm["t_end"], prm["t_step"]
    temps = list(range(t0, t1 - 1, -step)) if t0 > t1 else list(range(t0, t1 + 1, step))
    layers_per_level = py_round(10.0 / H)
    LEVEL = py_round(layers_per_level * H, 3)
    SLAB = 1.6                       # мост и перекрытие поверх уровня
    n_base = max(1, py_round(0.6 / H))
    BASE = py_round(n_base * H, 3)   # подложка: 3 слоя
    A = (104.0, 123.0, 118.0, 133.0)  # левая колонна (с подписью)
    B = (138.0, 123.0, 152.0, 133.0)  # правая колонна
    slab_box = (A[0], A[1], B[2], B[3])
    base_box = (96.0, 116.0, 160.0, 140.0)
    total = n_base + layers_per_level * len(temps)
    max_z = BASE + LEVEL * len(temps)
    title = text("temp_tower", ctx.lang, mat=m["type"], t0=str(temps[0]), t1=str(temps[-1]))
    start_gcode(g, temps[0], title, total, max_z)

    outer, inner, infill = 60, 100, 120
    n = 0
    for i in range(n_base):
        z = H * (i + 1)
        g.layer(n, z, H, total)
        w = ctx.W1 if i == 0 else W
        sp = 40 if i == 0 else infill
        perimeters(g, base_box, w, H, 40 if i == 0 else outer, sp, kind="base")
        o = 2 * w
        fill(g, (base_box[0] + o - 0.15 * w, base_box[1] + o - 0.15 * w, base_box[2] - o + 0.15 * w, base_box[3] - o + 0.15 * w),
             w, H, sp, i % 2 == 0, w, "base")
        n += 1

    for lvl, t in enumerate(temps):
        g.out(text("tower_level", ctx.lang, n=str(lvl + 1), t=str(t)))
        g.out(f"M104 S{t}")
        label = str(t)
        for k in range(layers_per_level):
            z = BASE + lvl * LEVEL + H * (k + 1)
            local = H * (k + 1)
            g.layer(n, z, H, total)
            if n == m["fan_off_layers"]:
                g.fan(m["fan"])
            layer_start = len(g.lines)
            t_0 = g.time
            if local <= LEVEL - SLAB + 1e-6:
                for box, has_label in ((A, True), (B, False)):
                    perimeters(g, box, W, H, outer, inner)
                    if has_label:
                        v = local - H / 2 - 1.8   # подпись: полоса 1.8..7.8 мм от низа уровня
                        if 0 <= v <= 6.0:
                            x0 = A[0] + (14.0 - (len(label) * 3.6 + (len(label) - 1) * 1.0)) / 2
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
            slow_layer(g, layer_start, t_0, m["min_layer_time"])
            n += 1
    name = file_name(ctx, "TempTower", m["type"], f"{temps[0]}-{temps[-1]}")
    return finish(g, name, title, max_z)


# ---------- линии опережения ----------

def pa_lines(ctx, prm):
    m = ctx.m
    g = Gcode(ctx)
    H = ctx.H
    W = ctx.W1
    count = py_round((prm["pa_end"] - prm["pa_start"]) / prm["pa_step"]) + 1
    values = [py_round(prm["pa_start"] + i * prm["pa_step"], 3) for i in range(count)]
    x_start, slow_len, fast_len = 60.0, 20.0, 40.0
    y0, step = 60.0, 5.0
    total = 2
    title = text("pa_lines", ctx.lang, mat=m["type"], v0=fixed(values[0], 3), v1=fixed(values[-1], 3))
    start_gcode(g, m["first_layer_temp"], title, total, 2 * H)
    fast = min(150.0, m["mvs"] * 0.9 / area(W, H))
    slow = 20.0

    g.layer(0, H, H, total)
    g.out(f"M104 S{m['nozzle_temp']}")
    g.fixed_temp = True
    frame = (x_start - 6, y0 - 6, x_start + 2 * slow_len + fast_len + 24, y0 + step * (len(values) - 1) + 6)
    perimeters(g, frame, W, H, 30, 30, n=2, kind="base")
    x_end = x_start + 2 * slow_len + fast_len
    for i, v in enumerate(values):
        y = y0 + i * step
        g.retract()
        g.travel(x_start, y)
        g.pressure_advance(v)
        g.out("M400")
        g.extrude(x_start + slow_len, y, W, H, slow, "slow", flow=1.0)
        g.extrude(x_start + slow_len + fast_len, y, W, H, fast, "fast", flow=1.0)
        g.extrude(x_end, y, W, H, slow, "slow", flow=1.0)
    g.pressure_advance(m["pa_default"], text("pa_restore", ctx.lang))
    for layer in (0, 1):
        if layer == 1:
            g.layer(1, 2 * H, H, total)
        for i, v in enumerate(values):
            y = y0 + i * step - 1.6
            txt = f"{py_round(v * 1000):03d}"
            for j, ch in enumerate(txt):
                for a, b in flat_digit_strokes(ch, x_end + 5 + j * 3.2, y):
                    if hypot(a[0] - g.x, a[1] - g.y) <= 2:
                        g.travel(*a, hop=False)
                    else:
                        g.travel(*a)
                    g.extrude(b[0], b[1], ctx.LW, H, 20, "label")
    name = file_name(ctx, "PressureAdvance_Lines", m["type"], f"{trim(values[0], 3)}-{fixed(values[-1], 3)}")
    return finish(g, name, title, 2 * H)


# ---------- поток ----------

def flow_test(ctx, prm):
    m = ctx.m
    g = Gcode(ctx)
    W, W1 = ctx.W, ctx.W1
    pcts = [prm["f_start"] + i * prm["f_step"] for i in range(9)]
    boxes = []
    for i, p in enumerate(pcts):
        cx = 94 + (i % 3) * 34
        cy = 167 - (i // 3) * 36
        boxes.append(((cx - 11, cy - 11, cx + 11, cy + 11), p))
    zs = layers_to(1.2, ctx.H)
    title = text("flow", ctx.lang, mat=m["type"], p0=str(pcts[0]), p1=str(pcts[-1]))
    start_gcode(g, m["first_layer_temp"], title, len(zs), zs[-1])

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
    return finish(g, file_name(ctx, "Flow", m["type"], f"{pcts[0]}-{pcts[-1]}"), title, zs[-1])


# ---------- откат ----------

def retraction_test(ctx, prm):
    m = ctx.m
    g = Gcode(ctx)
    W, W1 = ctx.W, ctx.W1
    values = [py_round(prm["r_start"] + i * prm["r_step"], 3) for i in range(prm["r_count"])]
    LEVEL, BASE = 5.0, 0.6
    A = (96.0, 124.0, 108.0, 132.0)
    B = (148.0, 124.0, 160.0, 132.0)
    base_box = (92.0, 120.0, 164.0, 136.0)
    zs = layers_to(BASE + LEVEL * len(values), ctx.H)
    title = text("retraction", ctx.lang, mat=m["type"], v0=trim(values[0], 2), v1=trim(values[-1], 2))
    start_gcode(g, m["first_layer_temp"], title, len(zs), zs[-1])

    def body(n, z, h):
        if z <= BASE + 1e-6:
            solid(g, base_box, n, w=W1 if n == 0 else W, h=h, wall_speed=40)
            return
        lvl = min(int((z - BASE - 1e-6) / LEVEL), len(values) - 1)
        if g.retract_len != values[lvl]:
            g.out(text("retraction_level", ctx.lang, n=str(lvl + 1), v=py_repr(values[lvl])))
            g.retract_len = values[lvl]
        local = z - BASE - lvl * LEVEL
        for box in (A, B):
            sparse(g, box, n, h=h)
            if box is A:
                txt = f"{py_round(values[lvl] * 10):02d}"
                emboss(g, txt, A[0] + (12 - text_width(txt, 2.6, 0.8)) / 2, A[1], local - h / 2 - 0.7,
                       W_=2.6, H_=3.6, S_=0.9, gap=0.8)

    run_layers(g, zs, body)
    return finish(g, file_name(ctx, "Retraction", m["type"], f"{trim(values[0], 2)}-{trim(values[-1], 2)}"), title, zs[-1])


# ---------- максимальный расход ----------

def max_flow_test(ctx, prm):
    m = ctx.m
    g = Gcode(ctx)
    W1 = ctx.W1
    WW, HH = ctx.WW, ctx.HH
    v0, v1 = float(prm["v_start"]), float(prm["v_end"])
    limit = ctx.MAX_SPEED * area(WW, HH)       # the printer's top speed caps the test
    if v1 > limit:
        v1 = float(math.floor(limit))
    low = 5.0 * area(WW, HH)                   # and 5 mm/s at the bottom (F300, the check's floor)
    if v0 < low:
        v0 = float(math.ceil(low))
    if v1 < v0 + 4:
        v1 = v0 + 4
    box = (78.0, 118.0, 178.0, 138.0)
    BASE = py_round(2 * ctx.H, 3)
    zs = layers_to(BASE, ctx.H) + [py_round(BASE + HH * (i + 1), 3) for i in range(py_round((v1 - v0) / HH))]
    title = text("max_flow", ctx.lang, mat=m["type"], v0=fixed(v0, 0), v1=fixed(v1, 0))
    start_gcode(g, m["first_layer_temp"], title, len(zs), zs[-1])
    g.accel(min(10000, ctx.p["max_accel"]))

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
        for mark in range(int(v0) + 4, int(v1), 4):
            v = (z - BASE) - (mark - v0) - HH / 2
            if 0 <= v <= 3.0:
                emboss(g, str(mark), box[0] + 4, box[1], v, W_=2.2, H_=3.0, S_=0.8, gap=0.7, h=HH)

    run_layers(g, zs, body, min_time=False)
    return finish(g, file_name(ctx, "MaxFlow", m["type"], f"{fixed(v0, 0)}-{fixed(v1, 0)}"), title, zs[-1])


# ---------- нависания и мосты ----------

def overhang_bridge_test(ctx, prm):
    m = ctx.m
    g = Gcode(ctx)
    W1 = ctx.W1
    angles = [20, 30, 40, 50, 60, 70, 80]
    spine = (60.0, 170.0, 134.0, 176.0)
    spine_base = (58.0, 168.0, 136.0, 178.0)
    fin_z0, top_ov = 1.0, 16.0
    lengths = [10, 20, 30, 40, 50]
    rows = [(60.0 + 0, 60.0 + i * 18) for i in range(len(lengths))]
    PILLAR_H, SLAB = 8.0, 1.0
    zs = layers_to(top_ov, ctx.H)
    title = text("overhang", ctx.lang, mat=m["type"], a0=str(angles[0]), a1=str(angles[-1]),
                 l0=str(lengths[0]), l1=str(lengths[-1]))
    start_gcode(g, m["first_layer_temp"], title, len(zs), zs[-1])

    def body(n, z, h):
        w = W1 if n == 0 else ctx.W
        if z <= fin_z0 + 1e-6:
            solid(g, spine_base, n, w=w, h=h, wall_speed=40)
        else:
            sparse(g, spine, n, h=h)
            for i, a in enumerate(angles):
                d = min(12.0, (z - fin_z0) * num.tan_deg(a))
                if d >= 1.0:
                    x = 62.0 + i * 10
                    solid(g, (x, spine[1] - d, x + 8, spine[1] + 0.5), n, h=h, wall_speed=40, fill_speed=60)
        if n < 2:
            for i, a in enumerate(angles):
                flat_text(g, str(a), 62.0 + i * 10 + 4 - text_width(str(a), 2.0, 1.2) / 2, spine[1] - 18, h)
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
    return finish(g, file_name(ctx, "OverhangBridge", m["type"]), title, zs[-1])


# ---------- первый слой ----------

def first_layer_test(ctx, prm):
    m = ctx.m
    g = Gcode(ctx)
    H = ctx.H
    zs = [H]
    title = text("first_layer", ctx.lang, mat=m["type"])
    start_gcode(g, m["first_layer_temp"], title, 1, H)
    bed = ctx.p["bed"]
    # 9 squares over the whole bed: 17 mm from the edges (frame coordinates).
    if bed["shape"] == "round":
        r = min(bed["x"], bed["y"]) / 2
        s = (r - 4) / math.sqrt(2) - 17
        xs = [128.0 - s, 128.0, 128.0 + s]
        ys = list(xs)
    else:
        lo_x, lo_y = -ctx.ox, -ctx.oy                 # printer 0 in the frame
        if bed["origin"] == "center":
            lo_x, lo_y = lo_x - bed["x"] / 2, lo_y - bed["y"] / 2
        xs = [lo_x + 34, lo_x + bed["x"] / 2, lo_x + bed["x"] - 34]
        ys = [lo_y + 34, lo_y + bed["y"] / 2, lo_y + bed["y"] - 34]

    def body(n, z, h):
        for cy in ys:
            for cx in (xs if cy != ys[0] else xs[::-1]):
                solid(g, (cx - 17, cy - 17, cx + 17, cy + 17), 0, w=ctx.W1, h=h, wall_speed=40, fill_speed=50)

    run_layers(g, zs, body, min_time=False)
    return finish(g, file_name(ctx, "FirstLayer", m["type"]), title, H)


# ---------- зазоры ----------

def tolerance_test(ctx, prm):
    m = ctx.m
    g = Gcode(ctx)
    gaps = list(prm["gaps"])
    PEG = 8.0
    zs = layers_to(6.0, ctx.H)
    title = text("tolerance", ctx.lang, mat=m["type"], g0=fixed(gaps[0], 2), g1=fixed(gaps[-1], 2))
    start_gcode(g, m["first_layer_temp"], title, len(zs), zs[-1])
    x_first = 128.0 - (len(gaps) - 1) * 11

    def body(n, z, h):
        w = ctx.W  # и первый слой той же ширины: широкий первый слой залил бы узкие зазоры
        sp = 30 if n == 0 else 60
        for i, gap in enumerate(gaps):
            cx, cy = x_first + i * 22, 128.0
            outer = (cx - 9, cy - 9, cx + 9, cy + 9)
            hole = (cx - PEG / 2 - gap, cy - PEG / 2 - gap, cx + PEG / 2 + gap, cy + PEG / 2 + gap)
            peg = (cx - PEG / 2, cy - PEG / 2, cx + PEG / 2, cy + PEG / 2)
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
                txt = f"{py_round(gap * 100):02d}"
                flat_text(g, txt, cx - text_width(txt, 2.0, 1.2) / 2, outer[1] - 6, h)

    run_layers(g, zs, body)
    return finish(g, file_name(ctx, "Tolerance", m["type"], f"{fixed(gaps[0], 2)}-{fixed(gaps[-1], 2)}"), title, zs[-1])


# ---------- размеры ----------

def cube_test(ctx, prm):
    m = ctx.m
    g = Gcode(ctx)
    size = prm["size"]
    half = size / 2
    box = (128.0 - half, 128.0 - half, 128.0 + half, 128.0 + half)
    zs = layers_to(float(size), ctx.H)
    bottom = max(3, py_round(0.8 / ctx.H))
    top = max(4, py_round(1.0 / ctx.H))
    label = str(size)
    title = text("cube", ctx.lang, mat=m["type"], s=label)
    start_gcode(g, m["first_layer_temp"], title, len(zs), zs[-1])

    def body(n, z, h):
        w = ctx.W1 if n == 0 else ctx.W
        if n < bottom or n >= len(zs) - top:
            solid(g, box, n, w=w, h=h, walls=3, wall_speed=40 if n == 0 else 60)
        else:
            sparse(g, box, n, h=h, walls=3)
        emboss(g, label, box[0] + (size - text_width(label, 3.6, 1.0)) / 2, box[1], z - h / 2 - (size / 2 - 3.0))

    run_layers(g, zs, body)
    return finish(g, file_name(ctx, f"Cube{label}", m["type"]), title, zs[-1])


# ---------- волны после углов ----------

def ringing_test(ctx, prm):
    m = ctx.m
    g = Gcode(ctx)
    W, H = ctx.W, ctx.H
    box = (98.0, 98.0, 158.0, 158.0)
    BAND, BASE = 5.0, 0.6
    accels = [prm["a_start"] + prm["a_step"] * i for i in range(prm["a_count"])]
    accels = [a for a in accels if a <= ctx.p["max_accel"]] or [min(prm["a_start"], ctx.p["max_accel"])]
    speed = min(150.0, m["mvs"] * 0.9 / area(W, H))
    zs = layers_to(BASE + BAND * len(accels), H)
    title = text("ringing", ctx.lang, mat=m["type"], a0=str(accels[0]), a1=str(accels[-1]))
    start_gcode(g, m["first_layer_temp"], title, len(zs), zs[-1])

    def body(n, z, h):
        if z <= BASE + 1e-6:
            solid(g, box, n, w=ctx.W1 if n == 0 else W, h=h, wall_speed=40)
            return
        band = min(int((z - BASE - 1e-6) / BAND), len(accels) - 1)
        local = z - BASE - band * BAND
        if local <= h + 1e-6:
            g.out(text("ringing_band", ctx.lang, n=str(band + 1), a=str(accels[band])))
            g.accel(accels[band], band=True)
        perimeters(g, box, W, h, speed, speed, n=2)
        emboss(g, str(band + 1), box[0] + 6, box[1], local - h / 2 - 0.7, W_=2.6, H_=3.6, S_=0.9, gap=0.8)

    run_layers(g, zs, body, min_time=False)
    rng = f"{trim(accels[0] / 1000, 1)}k-{trim(accels[-1] / 1000, 1)}k"
    return finish(g, file_name(ctx, "Ringing", m["type"], rng), title, zs[-1])


# ---------- список тестов ----------

BUILDERS = {
    "first_layer": first_layer_test,
    "temp_tower": temp_tower,
    "flow": flow_test,
    "pressure_advance": pa_lines,
    "retraction": retraction_test,
    "max_flow": max_flow_test,
    "overhang_bridge": overhang_bridge_test,
    "ringing": ringing_test,
    "tolerance": tolerance_test,
    "cube": cube_test,
}
TEST_IDS = list(BUILDERS)


def default_params(test_id, material, printer=None):
    t = material["tower"]
    return {
        "first_layer": {},
        "temp_tower": {"t_start": t["start"], "t_end": t["end"], "t_step": t["step"]},
        "flow": {"f_start": 80, "f_step": 5},
        "pressure_advance": {"pa_start": 0.0, "pa_end": 0.08, "pa_step": 0.005},
        "retraction": {"r_start": 0.2, "r_step": 0.2, "r_count": 8},
        "max_flow": {"v_start": material["max_flow"][0], "v_end": material["max_flow"][1]},
        "overhang_bridge": {},
        "ringing": {"a_start": 1000, "a_step": 1000, "a_count": 12},
        "tolerance": {"gaps": [0.1, 0.15, 0.2, 0.25, 0.3, 0.4]},
        "cube": {"size": 20},
    }[test_id]


def bounds(ctx, g):
    """Extent of the printed lines in printer coordinates: x1, y1, x2, y2."""
    xs = [c for s in g.segments for c in (s[0], s[2])]
    ys = [c for s in g.segments for c in (s[1], s[3])]
    return ctx.px(min(xs)), ctx.py(min(ys)), ctx.px(max(xs)), ctx.py(max(ys))


def fits(printer, box, margin=1.0):
    bed = printer["bed"]
    x1, y1, x2, y2 = box
    if bed["shape"] == "round":
        r = min(bed["x"], bed["y"]) / 2 - margin
        return all(hypot(x, y) <= r for x, y in ((x1, y1), (x1, y2), (x2, y1), (x2, y2)))
    if bed["origin"] == "center":
        lo_x, lo_y, hi_x, hi_y = -bed["x"] / 2, -bed["y"] / 2, bed["x"] / 2, bed["y"] / 2
    else:
        lo_x, lo_y, hi_x, hi_y = 0.0, 0.0, bed["x"], bed["y"]
    return x1 >= lo_x + margin and y1 >= lo_y + margin and x2 <= hi_x - margin and y2 <= hi_y - margin


def generate(printer, material, test_id, params=None, lang="ru"):
    """One test file. Shifted to the bed centre if the reference place does not fit."""
    prm = default_params(test_id, material, printer)
    if params:
        prm.update(params)
    build = BUILDERS[test_id]
    ctx = Ctx(printer, material, lang)
    res = build(ctx, prm)
    box = bounds(ctx, res.g)
    if fits(printer, box):
        return res
    bed = printer["bed"]
    cx = 0.0 if bed["origin"] == "center" else bed["x"] / 2
    cy = 0.0 if bed["origin"] == "center" else bed["y"] / 2
    shift = (cx - (box[0] + box[2]) / 2, cy - (box[1] + box[3]) / 2)
    ctx = Ctx(printer, material, lang, shift)
    res = build(ctx, prm)
    if not fits(printer, bounds(ctx, res.g)):
        raise DoesNotFit(f"{test_id}: does not fit the bed")
    return res
