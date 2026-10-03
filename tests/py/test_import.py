"""Import from a G-code (plan tasks 9-10): synthetic files of six slicers -> expected profile."""
import json
import re
from pathlib import Path

import pytest
from hypothesis import given, strategies as st

from calib3d.core import check as C
from calib3d.core import generator as G
from calib3d.core import importer as I
from calib3d.core import profiles as P
from calib3d.core import templates as T

DIR = Path(__file__).resolve().parents[1] / "import"
EXPECTED = {k: v for k, v in json.loads((DIR / "expected.json").read_text(encoding="utf-8")).items() if not k.startswith("_")}


def load(name):
    return I.parse((DIR / name).read_text(encoding="utf-8"), name)


def subset(want, got, path=""):
    for k, v in want.items():
        assert k in got, f"{path}{k} not found"
        if isinstance(v, dict):
            subset(v, got[k], path + k + ".")
        else:
            assert got[k] == v, f"{path}{k}: {got[k]!r} != {v!r}"


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_sample(name):
    exp, r = EXPECTED[name], load(name)
    assert r["slicer"] == exp["slicer"]
    assert r["firmware_from"] == exp["firmware_from"]
    assert r["warnings"] == exp["warnings"]
    subset(exp["printer"], r["printer"])
    subset(exp["material"], r["material"])
    assert r["missing"] == exp["missing"]
    for line in exp["start"]:
        assert line in r["start_gcode"], line
    for line in exp["start_absent"]:
        assert line not in r["start_gcode"], line
    for line in exp["end"]:
        assert line in r["end_gcode"], line
    for line in exp.get("end_absent", []):
        assert line not in r["end_gcode"], line
    assert len(r["replaced"]) == exp["replaced"]
    for rep in r["replaced"]:
        assert "{" in rep["after"] and rep["before"] != rep["after"]


@pytest.mark.parametrize("name,fw", [("elegoo.gcode", "klipper"), ("prusa.gcode", "marlin"),
                                     ("superslicer.gcode", "rrf"), ("bambu.gcode", "marlin")])
def test_firmware_from_commands_when_no_header(name, fw):
    text = re.sub(r"^; gcode_flavor = .*$", "", (DIR / name).read_text(encoding="utf-8"), flags=re.M)
    r = I.parse(text, name)
    assert r["printer"]["firmware"] == fw and r["firmware_from"] == "commands"


def test_unknown_firmware_is_reported():
    r = I.parse("G28\nM109 S200\n;LAYER:0\nG1 X1 Y1 E1\n", "x.gcode")
    assert "firmware" in r["missing"] and "firmware_unknown" in r["warnings"]


BASES = {"klipper": "generic-klipper", "marlin": "generic-marlin", "rrf": "generic-rrf"}


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_imported_profile_generates_valid_gcode(name):
    r = load(name)
    base = P.printer(BASES[r["printer"].get("firmware", "marlin")])
    mat_type = (r["material"].get("type") or "PLA").lower()
    base_mat = P.material(mat_type if mat_type in ("pla", "petg", "abs", "asa", "tpu") else "pla")
    printer, material = I.to_profiles(r, base, base_mat)
    assert P.validate_printer(printer) == [] and P.validate_material(material) == []
    for tid in ("first_layer", "pressure_advance", "cube"):
        res = G.generate(printer, material, tid)
        assert C.check_result(res, tid) == [], (name, tid)
        assert re.search(r"^M83\b", res.text, re.M)


def test_cura_absolute_extrusion_is_switched_back():
    r = load("cura.gcode")
    printer, material = I.to_profiles(r, P.printer("generic-marlin"), P.material("pla"))
    lines = G.generate(printer, material, "cube").text.split("\n")
    i = lines.index("M82 ;absolute extrusion mode")
    assert "M83" in lines[i:lines.index(";LAYER_CHANGE")]


@pytest.mark.parametrize("pid", ["elegoo-centauri-carbon", "generic-klipper", "prusa-mk4"])
@pytest.mark.parametrize("mid", ["petg", "pla"])
def test_roundtrip_start_code(pid, mid):
    """Law: import(generated file).start expanded again == the original expanded start."""
    p, m = P.printer(pid), P.material(mid)
    res = G.generate(p, m, "flow")
    r = I.parse(res.text, "x.gcode")
    ctx = G.Ctx(p, m)
    zs_total = 6
    values, flags = G.template_values(ctx, m["first_layer_temp"], "t", zs_total, 1.2)
    original, _ = T.expand(p["start_gcode"], values, flags)
    again, unknown = T.expand(r["start_gcode"], values, flags)
    assert unknown == []
    clean = [s for s in original if not re.match(r"^;TYPE:", s)]
    while clean and not clean[-1].strip():
        clean.pop()
    assert again == clean
    assert r["material"]["first_layer_temp"] == m["first_layer_temp"] and r["material"]["bed"] == m["bed"]


@given(st.text(max_size=400))
def test_parse_never_crashes(text):
    r = I.parse(text)
    assert set(r) >= {"printer", "material", "start_gcode", "end_gcode", "missing", "replaced"}
    for line in r["start_gcode"] + r["end_gcode"]:
        assert "\n" not in line
