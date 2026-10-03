"""The G-code check: all bundled profiles pass, and each kind of fault is caught."""
import re

import pytest
from hypothesis import given, strategies as st

from calib3d.core import check as C
from calib3d.core import generator as G
from calib3d.core import profiles as P

PRINTERS = [p["id"] for p in P.printers()]
MATS = [m["id"] for m in P.materials()]
MATRIX = [(pid, tid) for pid in PRINTERS for tid in G.TEST_IDS]


@pytest.mark.parametrize("pid,test_id", MATRIX)
def test_every_profile_passes(pid, test_id):
    m = MATS[(PRINTERS.index(pid) + G.TEST_IDS.index(test_id)) % len(MATS)]
    r = G.generate(P.printer(pid), P.material(m), test_id)
    assert C.check_result(r, test_id) == []


_cache = {}


def base(pid="elegoo-centauri-carbon", mat="petg", tid="cube"):
    key = (pid, mat, tid)
    if key not in _cache:
        _cache[key] = G.generate(P.printer(pid), P.material(mat), tid)
    return _cache[key]


def codes(r, text, tid="cube"):
    g = r.g
    return {p.split(":")[0] for p in C.check(text, g.ctx.p, g.ctx.m, tid, g.body_start, g.body_end, r.max_z)}


def body_lines(r, pred):
    lines = r.text.split("\n")
    return [i for i in range(r.g.body_start, r.g.body_end) if pred(lines[i])]


def edit(r, i, new):
    lines = r.text.split("\n")
    lines[i] = new
    return "\n".join(lines)


EXTRUDE = re.compile(r"^G1 X\S+ Y\S+ E(\S+) F\S+$")


@given(st.integers(min_value=0, max_value=10**6))
def test_negative_extrusion_caught(k):
    r = base()
    idx = body_lines(r, EXTRUDE.match)
    i = idx[k % len(idx)]
    line = r.text.split("\n")[i]
    assert "extrusion" in codes(r, edit(r, i, line.replace(" E", " E-", 1)))


@given(st.integers(min_value=0, max_value=10**6), st.sampled_from([0.05, 10.0]))
def test_implausible_extrusion_caught(k, factor):
    r = base()
    idx = body_lines(r, EXTRUDE.match)
    i = idx[k % len(idx)]
    line = r.text.split("\n")[i]
    e = float(EXTRUDE.match(line).group(1))
    if e < 0.01:   # very short moves: rounding of E to 5 digits already dominates
        return
    assert "extrusion" in codes(r, edit(r, i, line.replace(f"E{e:.5f}", f"E{e * factor:.5f}")))


@given(st.integers(min_value=0, max_value=10**6), st.sampled_from([-5.0, 300.0]))
def test_outside_bed_caught(k, x):
    r = base()
    idx = body_lines(r, EXTRUDE.match)
    i = idx[k % len(idx)]
    line = r.text.split("\n")[i]
    assert "outside_bed" in codes(r, edit(r, i, re.sub(r"X\S+", f"X{x:.3f}", line, count=1)))


def test_fast_and_slow_moves_caught():
    r = base()
    i = body_lines(r, EXTRUDE.match)[10]
    line = r.text.split("\n")[i]
    assert "speed" in codes(r, edit(r, i, re.sub(r"F\S+$", "F99999", line)))
    assert "speed" in codes(r, edit(r, i, re.sub(r"F\S+$", "F120", line)))


def test_z_above_maximum_caught():
    r = base()
    i = body_lines(r, lambda s: s.startswith("G1 Z"))[3]
    assert "z_max" in codes(r, edit(r, i, "G1 Z400.000 F9000"))


@pytest.mark.parametrize("fw_line,pid", [("M900 K0.02", "elegoo-centauri-carbon"), ("M572 D0 S0.02", "elegoo-centauri-carbon"),
                                          ("SET_PRESSURE_ADVANCE ADVANCE=0.02", "generic-marlin"),
                                          ("SET_VELOCITY_LIMIT ACCEL=1000", "generic-rrf")])
def test_foreign_firmware_command_caught(fw_line, pid):
    r = base(pid, "pla")
    i = body_lines(r, lambda s: s.startswith(";LAYER:"))[1]
    assert "foreign_command" in codes(r, edit(r, i, fw_line))


def test_prusa_mk4_own_m572_is_fine():
    r = G.generate(P.printer("prusa-mk4"), P.material("pla"), "pressure_advance")
    assert "M572 S0.040" in r.text and C.check_result(r, "pressure_advance") == []


def test_leftover_placeholder_caught():
    r = base()
    assert "placeholder" in codes(r, edit(r, 20, "M140 S{bed_temp}"))


def test_temperatures_caught():
    r = base()
    i = body_lines(r, lambda s: s.startswith(";LAYER:"))[2]
    assert "temperature" in codes(r, edit(r, i, "M104 S400"))
    assert "temperature" in codes(r, edit(r, i, "M140 S20"))


def test_acceleration_caught():
    r = base()
    i = body_lines(r, lambda s: s.startswith(";LAYER:"))[2]
    assert "accel" in codes(r, edit(r, i, "SET_VELOCITY_LIMIT ACCEL=99999"))
    assert "accel" in codes(r, edit(r, i, "M204 S99999"))


def test_missing_retract_caught():
    r = base()
    i = body_lines(r, lambda s: s.startswith("G1 E-"))[3]
    assert "retraction" in codes(r, edit(r, i, ";"))


def test_unslowed_layers_caught():
    r = base("elegoo-centauri-carbon", "petg", "cube")
    fast = re.sub(r"^(G1 X\S+ Y\S+ E\S+) F\d+$", r"\1 F6000", r.text, flags=re.M)
    assert "min_layer_time" in codes(r, fast)


def test_layer_order_caught():
    r = base()
    i = body_lines(r, lambda s: s.startswith(";Z:"))[5]
    assert "layers" in codes(r, edit(r, i, ";Z:0.10"))
