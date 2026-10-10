"""Laws from the independent review before 1.0.0 (plan task 21).

- The end code stays on the bed. The G-code check looks at the body only, and the end
  code of the delta profile parked at the rectangular corner (X-95 Y95): 134 mm from the centre of a 100 mm round bed, "move out of range" on Klipper
  at the end of every print, and M84 never ran.
- Invalid parameters never reach G-code: generate() refuses them (both windows used to keep
  a bad value and still write files with it, e.g. a 200 % flow plate or M104 S900).
- File names carry no characters a disk refuses (the prefix is free text in own profiles).
- A malformed ACCEL in own start code is skipped by the check, as in JavaScript, instead of
  crashing it.
"""
import math
import re

import pytest

from calib3d.core import check as C
from calib3d.core import generator as G
from calib3d.core import profiles as P

PRINTERS = [p["id"] for p in P.printers()]


def _xy_moves(text):
    """Absolute X/Y positions of every G0/G1 move of the whole file."""
    x = y = None
    absolute = True
    for line in text.splitlines():
        code = line.split(";", 1)[0].split()
        if not code:
            continue
        head = code[0].upper()
        if head == "G90":
            absolute = True
        elif head == "G91":
            absolute = False
        elif head in ("G0", "G1") and absolute:
            w = {c[0].upper(): c[1:] for c in code[1:]}
            if "X" in w:
                x = float(w["X"])
            if "Y" in w:
                y = float(w["Y"])
            if ("X" in w or "Y" in w) and x is not None and y is not None:
                yield x, y


@pytest.mark.parametrize("pid", PRINTERS)
def test_end_code_stays_on_the_bed(pid):
    # Only where the end code parks at our {park_x} {park_y}: Centauri Carbon wipes the nozzle
    # off the bed (Y-1.2) and parks behind it (Y264.5) by design, and that code is the printed
    # and checked reference.
    p = P.printer(pid)
    if not any("{park_" in s for s in p["end_gcode"]):
        pytest.skip("own vendor parking")
    bed = p["bed"]
    r = G.generate(p, P.material("pla"), "first_layer")
    end = r.g.lines[r.g.body_end:]
    moves = list(_xy_moves("\n".join(["G90"] + end)))
    assert moves, pid      # every profile parks the head
    for x, y in moves:
        if bed["shape"] == "round":
            assert math.hypot(x, y) <= min(bed["x"], bed["y"]) / 2 + 1e-6, (pid, x, y)
        elif bed["origin"] == "center":
            assert abs(x) <= bed["x"] / 2 and abs(y) <= bed["y"] / 2, (pid, x, y)
        else:
            assert 0 <= x <= bed["x"] and 0 <= y <= bed["y"], (pid, x, y)


def test_delta_parks_inside_the_round_bed():
    end = G.generate(P.printer("generic-delta-klipper"), P.material("pla"), "cube").text
    tail = end[end.rindex(";END") if ";END" in end else -2000:]
    assert "X-95" not in tail and "Y95" not in tail


@pytest.mark.parametrize("params", [{"f_start": 120, "f_step": 10}, {"f_start": float("nan")}])
def test_invalid_parameters_are_refused(params):
    with pytest.raises(G.ParamError):
        G.generate(P.printer("elegoo-centauri-carbon"), P.material("petg"), "flow", params)


def test_temperature_out_of_range_is_refused():
    with pytest.raises(G.ParamError):
        G.generate(P.printer("generic-klipper"), P.material("pla"), "temp_tower", {"t_start": 900})


def test_file_names_are_safe_for_the_disk():
    p = P.printer("generic-klipper")
    p["prefix"] = 'my/printer:"1"?'
    r = G.generate(p, P.material("pla"), "cube")
    assert re.fullmatch(r"[A-Za-z0-9._+-]+\.gcode", r.name), r.name


def test_malformed_accel_in_own_start_code_does_not_crash_the_check():
    p = P.printer("generic-klipper")
    p["start_gcode"] = list(p["start_gcode"]) + ["SET_VELOCITY_LIMIT ACCEL=abc"]
    r = G.generate(p, P.material("pla"), "cube")
    assert isinstance(C.check_result(r, "cube"), list)
