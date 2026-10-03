"""Test parameters, time and grams, the result helper (plan task 8)."""
import re

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from calib3d.core import check as C
from calib3d.core import generator as G
from calib3d.core import params as PR
from calib3d.core import profiles as P

CC = P.printer("elegoo-centauri-carbon")


def test_tests_json_matches_the_generator():
    assert [t["id"] for t in PR.tests()] == G.TEST_IDS
    for t in PR.tests():
        keys = {s["key"] for s in t["params"]}
        assert keys == set(G.default_params(t["id"], P.material("pla"))), t["id"]
        for k in ("name", "look", "result"):
            assert t[k]["ru"] and t[k]["en"]


@pytest.mark.parametrize("pid", [p["id"] for p in P.printers()])
def test_defaults_are_valid(pid):
    p = P.printer(pid)
    for m in P.materials():
        for tid in G.TEST_IDS:
            assert PR.validate(tid, G.default_params(tid, m), p, m) == [], (pid, m["id"], tid)


def test_tower_range_changes_levels_and_name():
    r = G.generate(CC, P.material("petg"), "temp_tower", {"t_start": 250, "t_end": 230, "t_step": 10})
    assert r.name == "ECC_0.4_TempTower_PETG_250-230.gcode"
    assert re.findall(r"^M104 S(\d+)$", r.text, re.M)[1:] == ["250", "240", "230"]
    assert C.check_result(r, "temp_tower") == []


def test_tower_can_go_upwards():
    r = G.generate(CC, P.material("pla"), "temp_tower", {"t_start": 190, "t_end": 210, "t_step": 10})
    assert re.findall(r"^M104 S(\d+)$", r.text, re.M)[1:] == ["190", "200", "210"]


def test_pa_range():
    r = G.generate(CC, P.material("pla"), "pressure_advance", {"pa_start": 0.02, "pa_end": 0.1, "pa_step": 0.01})
    vals = re.findall(r"^SET_PRESSURE_ADVANCE ADVANCE=(\S+)$", r.text, re.M)
    assert vals == ["0.020", "0.030", "0.040", "0.050", "0.060", "0.070", "0.080", "0.090", "0.100"]
    assert r.name.endswith("_0.02-0.100.gcode")


def test_ringing_is_capped_by_the_printer():
    p = P.printer("generic-marlin")      # max 3000 mm/s²
    r = G.generate(p, P.material("pla"), "ringing")
    assert re.findall(r"^M204 S(\d+)$", r.text, re.M)[1:] == ["1000", "2000", "3000"]
    assert r.name.endswith("_1k-3k.gcode")


def test_custom_gaps():
    r = G.generate(CC, P.material("pla"), "tolerance", {"gaps": [0.05, 0.1, 0.2]})
    assert r.name.endswith("_0.05-0.20.gcode") and C.check_result(r, "tolerance") == []


@pytest.mark.parametrize("test_id,prm,key", [
    ("temp_tower", {"t_start": 230, "t_end": 230, "t_step": 5}, "t_end"),
    ("temp_tower", {"t_start": 300, "t_end": 200, "t_step": 1}, "t_step"),
    ("pressure_advance", {"pa_start": 0.1, "pa_end": 0.05, "pa_step": 0.005}, "pa_end"),
    ("pressure_advance", {"pa_start": 0.0, "pa_end": 1.0, "pa_step": 0.005}, "pa_step"),
    ("max_flow", {"v_start": 10, "v_end": 12}, "v_end"),
    ("tolerance", {"gaps": [0.3, 0.2]}, "gaps"),
    ("tolerance", {"gaps": [0.1]}, "gaps"),
    ("cube", {"size": 5}, "size"),
    ("ringing", {"a_start": 30000, "a_step": 1000, "a_count": 4}, "a_start"),
])
def test_bad_params_refused(test_id, prm, key):
    errors = PR.validate(test_id, prm, CC, P.material("pla"))
    assert any(e.startswith(key + ":") for e in errors), errors


def _footer(text):
    g = float(re.search(r"filament used \[g\] = (\S+)", text).group(1))
    h, m = re.search(r"printing time \(normal mode\) = (\d+)h (\d+)m", text).groups()
    return g, int(h) * 60 + int(m)


@pytest.mark.parametrize("test_id", G.TEST_IDS)
def test_time_and_grams_match_the_footer(test_id):
    r = G.generate(CC, P.material("petg"), test_id)
    s = PR.summary(r)
    grams, minutes = _footer(r.text)
    assert s["minutes"] == minutes and abs(float(s["grams"]) - grams) <= 0.05
    assert r.grams == pytest.approx(r.g.e_total * r.g.ctx.FIL_AREA / 1000 * 1.27)
    assert minutes > 3 and grams > 0.3


def test_reference_times():
    # README of the reference: tower PETG 1 h 15 min, flow 19 min, PA 7 min, cube 18 min
    expect = {"temp_tower": 75, "flow": 19, "pressure_advance": 7, "cube": 18, "first_layer": 11}
    for tid, minutes in expect.items():
        assert abs(PR.summary(G.generate(CC, P.material("petg"), tid))["minutes"] - minutes) <= 1, tid


params_st = st.fixed_dictionaries({
    "temp_tower": st.tuples(st.integers(180, 280), st.integers(180, 280), st.sampled_from([5, 10])),
    "pa": st.tuples(st.sampled_from([0.0, 0.01, 0.02]), st.integers(4, 20), st.sampled_from([0.002, 0.005, 0.01])),
    "retr": st.tuples(st.sampled_from([0.1, 0.2, 0.5]), st.sampled_from([0.1, 0.2, 0.25]), st.integers(2, 10)),
    "ring": st.tuples(st.sampled_from([500, 1000, 2000]), st.sampled_from([500, 1000]), st.integers(2, 12)),
    "pid": st.sampled_from([p["id"] for p in P.printers()]),
    "mid": st.sampled_from([m["id"] for m in P.materials()]),
    "test": st.sampled_from(["temp_tower", "pressure_advance", "retraction", "ringing"]),
})


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(params_st)
def test_random_valid_params_pass_the_check(d):
    p, m = P.printer(d["pid"]), P.material(d["mid"])
    t0, t1, ts = d["temp_tower"]
    prm = {"temp_tower": {"t_start": t0, "t_end": t1 if t1 != t0 else t0 - ts, "t_step": ts},
           "pressure_advance": {"pa_start": d["pa"][0], "pa_end": round(d["pa"][0] + d["pa"][1] * d["pa"][2], 3), "pa_step": d["pa"][2]},
           "retraction": {"r_start": d["retr"][0], "r_step": d["retr"][1], "r_count": d["retr"][2]},
           "ringing": {"a_start": d["ring"][0], "a_step": d["ring"][1], "a_count": d["ring"][2]}}[d["test"]]
    if d["test"] == "temp_tower":
        lo, hi = sorted((prm["t_start"], prm["t_end"]))
        m["tower"] = {"start": prm["t_start"], "end": prm["t_end"], "step": ts}
    if PR.validate(d["test"], prm, p, m):
        return
    r = G.generate(p, m, d["test"], prm)
    assert C.check_result(r, d["test"]) == []


@pytest.mark.parametrize("test_id,text,value", [
    ("temp_tower", "245", "245"), ("flow", "104", "1.040"), ("pressure_advance", "024", "0.024"),
    ("pressure_advance", "0.035", "0.035"), ("retraction", "08", "0.8"), ("retraction", "1.2", "1.2"),
    ("max_flow", "20", "17.0"), ("overhang_bridge", "60", "30"), ("ringing", "5", "4000"),
    ("ringing", "1", "500"), ("tolerance", "15", "0.15"), ("tolerance", "0.2", "0.20"),
    ("cube", "20.02 19.98 20.05", "OK"), ("cube", "19.7 19.7 19.9", "1.015"), ("cube", "20.0 19.6 20.0", "Y"),
])
def test_helper(test_id, text, value):
    m = P.material("petg")
    out = PR.helper(test_id, text, CC, m, G.default_params(test_id, m))
    assert out["ok"] and out["value"] == value, out


def test_helper_errors():
    m = P.material("pla")
    assert PR.helper("flow", "", CC, m, {})["error"] == "need_number"
    assert PR.helper("cube", "20 20", CC, m, {"size": 20})["error"] == "need_three"
    assert PR.helper("ringing", "40", CC, m, G.default_params("ringing", m))["error"] == "out_of_range"
    assert PR.helper("first_layer", "1", CC, m, {})["error"] == "no_helper"


def test_helper_flow_uses_the_current_ratio():
    pla = P.material("pla")      # flow 0.98
    assert PR.helper("flow", "104", CC, pla, {})["value"] == "1.019"
