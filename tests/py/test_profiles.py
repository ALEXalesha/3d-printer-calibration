"""Profiles: shared JSON files, the loader and its schema check."""
import copy
import json

import pytest
from hypothesis import given, strategies as st

from calib3d.core import profiles as P
from helpers import reference

PRINTERS = P.printers()
MATERIALS = P.materials()


def test_bundled_profiles_are_valid():
    assert len(PRINTERS) >= 14
    for p in PRINTERS:
        assert P.validate_printer(p) == [], p["id"]
    for m in MATERIALS:
        assert P.validate_material(m) == [], m["id"]


def test_ids_unique_and_file_names_match():
    for kind in ("printers", "materials"):
        for path in (P.profiles_dir() / kind).glob("*.json"):
            assert json.loads(path.read_text(encoding="utf-8"))["id"] == path.stem
    assert len({p["prefix"] for p in PRINTERS}) == len(PRINTERS)


def test_only_centauri_carbon_is_verified():
    assert [p["id"] for p in PRINTERS if p["verified"]] == ["elegoo-centauri-carbon"]
    for p in PRINTERS:
        if not p["verified"] and not p["id"].startswith("generic-"):
            assert "warning" in p and "source" in p, p["id"]


def test_petg_and_pla_are_the_reference_values():
    ref = reference().MATERIALS
    for mid, name in (("petg", "PETG"), ("pla", "PLA")):
        m, r = P.material(mid), ref[name]
        t = m["tower"]
        assert list(range(t["start"], t["end"] - 1, -t["step"])) == r["temps"]
        assert (m["type"], m["nozzle_temp"], m["first_layer_temp"]) == (r["type"], r["first_temp"], r["first_temp"])
        for k in ("bed", "flow", "mvs", "fan", "bridge_fan", "fan_off_layers", "min_layer_time", "pa_default"):
            assert m[k] == r[k], (mid, k)


def test_centauri_carbon_is_the_reference_printer():
    ref = reference()
    p = P.printer("elegoo-centauri-carbon")
    assert p["bed"]["x"] == p["bed"]["y"] == ref.BED
    assert (p["retract"]["length"], p["retract"]["speed"] * 60, p["retract"]["z_hop"]) == (ref.RETRACT, ref.RETRACT_F, ref.ZHOP)
    assert p["travel_speed"] * 60 == ref.TRAVEL_F and p["default_accel"] == ref.ACCEL
    assert p["options"] == {"canvas": True, "nozzle_wipe": True}


def test_firmware_table_complete_with_links():
    fw = P.firmware()
    for fid in ("klipper", "marlin", "rrf"):
        f = fw[fid]
        for k in ("pressure_advance", "accel", "accel_band", "fan", "signature", "docs"):
            assert k in f, (fid, k)
        for k in ("pressure_advance", "accel", "fan"):
            assert f["docs"][k]["url"].startswith("https://"), (fid, k)
    assert fw["klipper"]["pressure_advance"].startswith("SET_PRESSURE_ADVANCE")
    assert fw["marlin"]["pressure_advance"].startswith("M900 K")
    assert fw["rrf"]["pressure_advance"].startswith("M572 D0 S")


REQUIRED = [s[0] for s in P.schema()["printer"]]


@given(st.sampled_from(REQUIRED), st.sampled_from([None, "x", -1, 1e9, [], True]))
def test_schema_rejects_broken_printer(field, value):
    p = copy.deepcopy(PRINTERS[0])
    parts = field.split(".")
    cur = p
    for part in parts[:-1]:
        cur = cur[part]
    if value is None:
        del cur[parts[-1]]
    else:
        cur[parts[-1]] = value
    errors = P.validate_printer(p)
    # some replacements are still valid values for some fields (e.g. True for a bool)
    spec = next(s for s in P.schema()["printer"] if s[0] == field)
    if value is True and spec[1] == "bool":
        return
    if value == "x" and spec[1] == "str":
        return
    assert errors, (field, value)


@pytest.mark.parametrize("field,value", [("tower.step", 0), ("bed", 200), ("max_flow", [10, 5]), ("fan", 1.5), ("nozzle_temp", 200.5)])
def test_schema_rejects_broken_material(field, value):
    m = copy.deepcopy(MATERIALS[0])
    cur = m
    parts = field.split(".")
    for part in parts[:-1]:
        cur = cur[part]
    cur[parts[-1]] = value
    assert P.validate_material(m)


def test_round_bed_needs_center_origin():
    p = copy.deepcopy(PRINTERS[0])
    p["bed"]["shape"] = "round"
    p["bed"]["origin"] = "corner"
    assert any("round" in e for e in P.validate_printer(p))
