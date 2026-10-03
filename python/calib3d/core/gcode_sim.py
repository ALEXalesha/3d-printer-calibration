"""A very small G-code reader: where the head ends up after the start code.

Used when a profile has no explicit start_state (imported and generic profiles): the first
travel of a test starts from there, and the purge filament is counted in the grams.
"""
import re

_WORD = re.compile(r"([A-Z])([-+]?\d*\.?\d+)")


def words(line):
    code = line.split(";", 1)[0].strip().upper()
    if not code:
        return None, {}
    parts = code.split(None, 1)
    head = parts[0]
    rest = parts[1] if len(parts) > 1 else ""
    return head, {k: float(v) for k, v in _WORD.findall(rest)}


def end_state(lines, heat_time=240.0):
    x = y = z = 0.0
    e_total = 0.0
    absolute = True
    e_absolute = False
    e_pos = 0.0
    for line in lines:
        head, w = words(line)
        if head is None:
            continue
        if head == "G90":
            absolute = True
        elif head == "G91":
            absolute = False
        elif head == "M82":
            e_absolute = True
        elif head == "M83":
            e_absolute = False
        elif head == "G92":
            if "E" in w:
                e_pos = w["E"]
            x = w.get("X", x)
            y = w.get("Y", y)
            z = w.get("Z", z)
        elif head == "G28":
            if not w or "X" in w:
                x = 0.0
            if not w or "Y" in w:
                y = 0.0
            if not w or "Z" in w:
                z = 0.0
        elif head in ("G0", "G1", "G2", "G3"):
            if absolute:
                x, y, z = w.get("X", x), w.get("Y", y), w.get("Z", z)
            else:
                x, y, z = x + w.get("X", 0.0), y + w.get("Y", 0.0), z + w.get("Z", 0.0)
            if "E" in w:
                if e_absolute:
                    de = w["E"] - e_pos
                    e_pos = w["E"]
                else:
                    de = w["E"]
                if de > 0:
                    e_total += de
    return {"x": x, "y": y, "z": z, "e": e_total, "time": heat_time}
