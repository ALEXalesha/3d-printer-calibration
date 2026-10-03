"""Start/end templates: markers, options of the Centauri Carbon profile, nothing left over."""
import copy
import re

import pytest

from calib3d.core import generator as G
from calib3d.core import profiles as P
from calib3d.core import templates as T

BRACE = re.compile(r"\{[^{}\n]*\}")


def test_expand_basics():
    out, unknown = T.expand(["A{x}B", "{?f}only if f", "{?!f}only if not f", "{y}"], {"x": "1", "y": "a\nb"}, {"f": True})
    assert out == ["A1B", "only if f", "a", "b"] and unknown == []
    out, unknown = T.expand(["{?f}x", "{zz} {zz} {q}"], {}, {})
    assert out == ["{zz} {zz} {q}"] and unknown == ["zz", "q"]


def test_unknown_placeholder_refused():
    p = P.printer("generic-klipper")
    p["start_gcode"] = p["start_gcode"] + ["M117 {no_such_thing}"]
    with pytest.raises(G.TemplateError) as e:
        G.generate(p, P.material("pla"), "first_layer")
    assert e.value.names == ["no_such_thing"]


@pytest.mark.parametrize("pid", [p["id"] for p in P.printers()])
def test_no_braces_left_in_any_profile(pid):
    """Law: after expansion no '{...}' remains, for every profile and material."""
    for m in P.materials():
        r = G.generate(P.printer(pid), m, "first_layer")
        assert not BRACE.search(r.text), (pid, m["id"], BRACE.search(r.text).group(0))


def _cc(**options):
    p = P.printer("elegoo-centauri-carbon")
    p["options"].update(options)
    return p


def test_canvas_and_wipe_are_options():
    pla = P.material("pla")
    text = G.generate(_cc(), pla, "first_layer").text
    assert "M6211 A1 L200 T0 Q210 R210 S210" in text and "M729 ;Clean Nozzle" in text
    text = G.generate(_cc(canvas=False), pla, "first_layer").text
    assert "M6211" not in text and "M729" in text
    text = G.generate(_cc(nozzle_wipe=False), pla, "first_layer").text
    assert "M729" not in text and "M6211" in text


def test_pla_jam_fan_only_for_pla_on_a_hot_bed():
    cc = P.printer("elegoo-centauri-carbon")
    assert "M106 P3 S255" in G.generate(cc, P.material("pla"), "first_layer").text
    assert "M106 P3 S255" not in G.generate(cc, P.material("petg"), "first_layer").text
    cool = P.material("pla")
    cool["bed"] = 45
    assert "M106 P3 S255" not in G.generate(cc, cool, "first_layer").text


def test_end_lift_rule():
    cc = P.printer("elegoo-centauri-carbon")
    v, _ = G.template_values(G.Ctx(cc, P.material("pla")), 210, "t", 1, 90.6)
    assert v["max_z_plus_50_capped"] == "100" and v["max_z_plus_half"] == "91.10"
    v, _ = G.template_values(G.Ctx(cc, P.material("pla")), 210, "t", 1, 220.0)
    assert v["max_z_plus_50_capped"] == "256.50"
    small = P.printer("generic-klipper")
    small["bed"]["z"] = 80.0
    v, _ = G.template_values(G.Ctx(small, P.material("pla")), 210, "t", 1, 20.0)
    assert v["max_z_plus_50_capped"] == "30.00"


def test_placeholders_listing():
    names, flags = T.placeholders(P.printer("elegoo-centauri-carbon")["start_gcode"])
    assert "bed_temp" in names and "first_layer_nozzle_temp" in names
    assert set(flags) == {"canvas", "nozzle_wipe", "pla_hot_bed"}
