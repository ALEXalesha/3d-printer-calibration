"""G-code check: a small simulation of the finished file, independent of the generator.

It reads the text back (not the generator's own notes) and answers spec §7:
- everything inside the bed with a margin, Z not above the maximum;
- speeds and accelerations within the printer profile;
- extrusion positive and plausible for the line cross-section;
- temperatures within the material and the printer;
- minimum layer time kept (except tests where speed is the subject);
- no bare command of another firmware;
- every template placeholder expanded.

The JavaScript twin is web/js/core/check.js; both return the same list of problems.
Each problem is "code: details"; the codes are stable, tests look for them.
"""
import math
import re

from . import profiles
from .num import fixed, hypot, py_round, trim

_WORD = re.compile(r"([A-Z])([-+]?\d*\.?\d+)")
_BRACES = re.compile(r"\{[^{}\n]*\}")

# Tests where speed is what is being tested: no minimum layer time.
NO_MIN_TIME = ("max_flow", "ringing", "first_layer", "pressure_advance")
MIN_TIME_SHARE = 0.7

_NUM = re.compile(r"\s*[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?")


def _leading_float(s):
    """parseFloat of JavaScript: the leading number, NaN without one (and NaN compares false).
    float() raised on ACCEL={...} in own start code and the check crashed."""
    m = _NUM.match(str(s))
    return float(m.group(0)) if m else math.nan


def _parse(line):
    code = line.split(";", 1)[0].strip()
    if not code:
        return None, {}
    parts = code.split(None, 1)
    head = parts[0].upper()
    rest = parts[1] if len(parts) > 1 else ""
    if head.startswith(("SET_", "M", "G", "T")) and "=" in rest:
        return head, {k.upper(): v for k, v in re.findall(r"([A-Za-z_]+)=(\S+)", rest)}
    return head, {k: float(v) for k, v in _WORD.findall(rest.upper())}


def _foreign_words(printer):
    """Command words of other firmwares, minus what this printer's own commands use."""
    fws = profiles.firmware()
    own = printer["firmware"]
    from .generator import firmware_commands
    cmds = firmware_commands(printer)
    allowed = set()
    for v in cmds.values():
        for s in (v if isinstance(v, list) else [v] if v else []):
            allowed.add(s.split()[0].upper())
    foreign = set()
    for fid, fw in fws.items():
        if fid.startswith("_") or fid == own:
            continue
        foreign.update(w.upper() for w in fw["signature"])
    return foreign - allowed


def _inside(printer, x, y, margin):
    bed = printer["bed"]
    if bed["shape"] == "round":
        return hypot(x, y) <= min(bed["x"], bed["y"]) / 2 - margin
    if bed["origin"] == "center":
        return abs(x) <= bed["x"] / 2 - margin and abs(y) <= bed["y"] / 2 - margin
    return margin <= x <= bed["x"] - margin and margin <= y <= bed["y"] - margin


def check(text, printer, material, test_id, body_start=None, body_end=None, max_z=None, stats=None):
    """Problems of a G-code file; empty list - the file passes."""
    problems = []

    def bad(code, msg):
        if len([p for p in problems if p.startswith(code + ":")]) < 5:   # five of a kind is enough
            problems.append(f"{code}: {msg}")

    lines = text.split("\n")
    if text.endswith("\n"):
        lines = lines[:-1]
    n_lines = len(lines)
    b0 = 0 if body_start is None else body_start
    b1 = n_lines if body_end is None else body_end

    for i, line in enumerate(lines):
        m = _BRACES.search(line)
        if m:
            bad("placeholder", f"line {i + 1}: {m.group(0)}")

    foreign = _foreign_words(printer)
    nozzle = printer["nozzle"]
    fil_area = math.pi * (printer["filament_diameter"] / 2) * (printer["filament_diameter"] / 2)
    max_f_print = printer["max_speed"] * 60 + 0.5
    max_f_any = max(printer["max_speed"], printer["travel_speed"]) * 60 + 0.5
    t = material["tower"]
    t_lo = min(t["start"], t["end"], material["nozzle_temp"], material["first_layer_temp"]) - 15
    t_hi = max(t["start"], t["end"], material["nozzle_temp"], material["first_layer_temp"]) + 15
    z_top = printer["bed"]["z"]
    z_limit = (max_z + printer["retract"]["z_hop"] + 0.001) if max_z is not None else z_top
    h = py_round(0.5 * nozzle, 3)
    area_lo, area_hi = 0.2 * nozzle * h, 2.5 * nozzle * h
    use_min_time = test_id not in NO_MIN_TIME
    min_time = material["min_layer_time"]

    x = y = z = 0.0
    f = 0.0
    absolute = True
    layer_time = None
    layer_floor = True       # every extrusion of the layer at the 600 mm/min floor?
    layer_no = -1
    last_layer_z = -1.0
    retracted = 0.0

    def close_layer():
        if layer_time is None or not use_min_time or layer_no < 1:
            return
        if stats is not None and not layer_floor:
            stats.append(layer_time / min_time)
        # Like the reference, slowing scales only the printing moves; travel keeps its
        # speed, so a slowed layer ends below the minimum: about 90 % on the reference
        # profile, down to about 80 % for small layers and a long minimum. 70 % is the bar:
        # a layer printed at full speed is far below it.
        if layer_time < min_time * MIN_TIME_SHARE and not layer_floor:
            bad("min_layer_time", f"layer {layer_no}: {fixed(layer_time, 1)} s < {fixed(min_time, 1)} s")

    for i, line in enumerate(lines):
        head, w = _parse(line)
        in_body = b0 <= i < b1
        if line.startswith(";LAYER_CHANGE") and in_body:
            close_layer()
            layer_no += 1
            layer_time = 0.0
            layer_floor = True
        if in_body and line.startswith(";Z:"):
            lz = float(line[3:])
            if lz <= last_layer_z:
                bad("layers", f"line {i + 1}: layer Z {trim(lz, 3)} not above {trim(last_layer_z, 3)}")
            last_layer_z = lz
        if head is None:
            continue
        if head in foreign:
            bad("foreign_command", f"line {i + 1}: {head}")
        if head == "G90":
            absolute = True
        elif head == "G91":
            absolute = False
        elif head in ("M104", "M109") and "S" in w and w["S"] > 0 and in_body:
            if not t_lo <= w["S"] <= t_hi:
                bad("temperature", f"line {i + 1}: nozzle {trim(w['S'], 1)} outside {t_lo}..{t_hi}")
        elif head in ("M140", "M190") and "S" in w and w["S"] > 0:
            if w["S"] > 130 or abs(w["S"] - material["bed"]) > 0.5:
                bad("temperature", f"line {i + 1}: bed {trim(w['S'], 1)}, material {material['bed']}")
        elif head == "SET_VELOCITY_LIMIT" and "ACCEL" in w:
            if _leading_float(w["ACCEL"]) > printer["max_accel"]:
                bad("accel", f"line {i + 1}: {w['ACCEL']} > {printer['max_accel']}")
        elif head == "M204":
            for k in ("S", "P", "T"):
                if k in w and w[k] > printer["max_accel"]:
                    bad("accel", f"line {i + 1}: {trim(w[k], 1)} > {printer['max_accel']}")
        elif head in ("G0", "G1"):
            if "F" in w:
                f = w["F"]
            nx = w.get("X", x) if absolute else x + w.get("X", 0.0)
            ny = w.get("Y", y) if absolute else y + w.get("Y", 0.0)
            nz = w.get("Z", z) if absolute else z + w.get("Z", 0.0)
            e = w.get("E", 0.0)
            d = hypot(nx - x, ny - y)
            if in_body:
                if "Z" in w and (nz > z_limit + 1e-9 or nz > z_top):
                    bad("z_max", f"line {i + 1}: Z{trim(nz, 3)}")
                if d > 0:
                    if not _inside(printer, nx, ny, 0.0 if e <= 0 else 1.0):
                        bad("outside_bed", f"line {i + 1}: X{trim(nx, 3)} Y{trim(ny, 3)}")
                    if f < 300 - 1e-9:
                        bad("speed", f"line {i + 1}: F{trim(f, 1)} < 300")
                    if f > (max_f_print if e > 0 else max_f_any):
                        bad("speed", f"line {i + 1}: F{trim(f, 1)} above the printer limit")
                    if e < 0:
                        bad("extrusion", f"line {i + 1}: negative E on a move")
                    elif e > 0:
                        a = e * fil_area / d
                        if not area_lo <= a <= area_hi:
                            bad("extrusion", f"line {i + 1}: cross-section {fixed(a, 4)} mm2 not plausible for nozzle {trim(nozzle, 2)}")
                    if layer_time is not None and f > 0:
                        layer_time += d / (f / 60)
                        if e > 0 and f > 600.5:
                            layer_floor = False
                elif "Z" in w and layer_time is not None and f > 0:
                    layer_time += abs(nz - z) / (f / 60)
                if d == 0 and e != 0 and "X" not in w and "Y" not in w and "Z" not in w:
                    if layer_time is not None and f > 0:
                        layer_time += abs(e) / (f / 60)
                    if e < 0:
                        if retracted > 0:
                            bad("retraction", f"line {i + 1}: retract twice")
                        retracted = -e
                    else:
                        if retracted == 0:
                            bad("retraction", f"line {i + 1}: push back without a retract")
                        elif abs(e - retracted) > 0.0051:
                            bad("retraction", f"line {i + 1}: back {trim(e, 3)} after retract {trim(retracted, 3)}")
                        retracted = 0.0
            x, y, z = nx, ny, nz
    close_layer()
    return problems


def check_result(res, test_id):
    g = res.g
    return check(res.text, g.ctx.p, g.ctx.m, test_id, g.body_start, g.body_end, res.max_z)
