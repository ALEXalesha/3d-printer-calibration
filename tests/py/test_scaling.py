"""Nozzle and filament scaling (plan task 6): 0.4 is the golden; 0.2, 0.6, 0.8 pass the check."""
import re

import pytest

from calib3d.core import check as C
from calib3d.core import generator as G
from calib3d.core import profiles as P

MATS = [m["id"] for m in P.materials()]
CASES = [(pid, nz, tid) for pid in ("elegoo-centauri-carbon", "generic-marlin", "generic-delta-klipper")
         for nz in (0.2, 0.6, 0.8) for tid in G.TEST_IDS]


@pytest.mark.parametrize("pid,nozzle,test_id", CASES)
def test_other_nozzles_pass_the_check(pid, nozzle, test_id):
    p = P.printer(pid)
    p["nozzle"] = nozzle
    m = P.material(MATS[(G.TEST_IDS.index(test_id) + int(nozzle * 10)) % len(MATS)])
    r = G.generate(p, m, test_id)
    assert C.check_result(r, test_id) == []
    assert f"_{nozzle}_" in r.name


def test_line_sizes_follow_the_nozzle():
    for nz, w, w1, h in ((0.2, 0.225, 0.25, 0.1), (0.4, 0.45, 0.5, 0.2), (0.6, 0.675, 0.75, 0.3), (0.8, 0.9, 1.0, 0.4)):
        p = P.printer("generic-klipper")
        p["nozzle"] = nz
        c = G.Ctx(p, P.material("pla"))
        assert (c.W, c.W1, c.H, c.LW) == (w, w1, h, nz)
        heights = set(re.findall(r"^;HEIGHT:(\S+)$", G.generate(p, P.material("pla"), "cube").text, re.M))
        assert heights == {f"{h:.2f}"}


def test_filament_285_passes_and_extrudes_less():
    a = P.printer("generic-marlin")
    b = P.printer("generic-marlin")
    b["filament_diameter"] = 2.85
    ra = G.generate(a, P.material("pla"), "cube")
    rb = G.generate(b, P.material("pla"), "cube")
    assert C.check_result(rb, "cube") == []
    ratio = rb.g.e_total / ra.g.e_total
    assert 0.35 < ratio < 0.42          # (1.75/2.85)^2 = 0.377, start code purge aside
    assert "; filament_diameter: 2.85" in rb.text


def test_tower_levels_stay_ten_mm_apart_in_layers():
    for nz in (0.2, 0.6, 0.8):
        p = P.printer("generic-klipper")
        p["nozzle"] = nz
        r = G.generate(p, P.material("pla"), "temp_tower")
        zs = [float(z) for z in re.findall(r"^;Z:(\S+)$", r.text, re.M)]
        steps = {round(b - a, 2) for a, b in zip(zs, zs[1:])}
        assert steps == {round(0.5 * nz, 2)}, (nz, steps)
