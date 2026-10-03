"""Test parameters (ranges and steps) and the result helper.

profiles/tests.json describes the parameters for the UI; here they are checked, and the
helper turns "which level/line is best" into a number for the slicer profile.
Twin: web/js/core/params.js.
"""
import json
import re

from . import profiles
from .num import fixed, py_round, trim

_TESTS = None


def tests():
    global _TESTS
    if _TESTS is None:
        _TESTS = json.loads((profiles.profiles_dir() / "tests.json").read_text(encoding="utf-8"))["tests"]
    return _TESTS


def test_info(test_id):
    for t in tests():
        if t["id"] == test_id:
            return t
    raise KeyError(test_id)


def _levels(a, b, step):
    return abs(a - b) // step + 1


def validate(test_id, prm, printer, material):
    """Problems of a parameter set: list of "key: message" (empty - fine)."""
    errors = []
    for spec in test_info(test_id)["params"]:
        k = spec["key"]
        if k not in prm:
            errors.append(f"{k}: missing")
            continue
        v = prm[k]
        if spec["type"] == "list":
            if not isinstance(v, list) or not 2 <= len(v) <= 8:
                errors.append(f"{k}: 2..8 values")
                continue
            if any(not isinstance(x, (int, float)) or isinstance(x, bool) or not spec["min"] <= x <= spec["max"] for x in v):
                errors.append(f"{k}: values {spec['min']}..{spec['max']}")
            elif any(b <= a for a, b in zip(v, v[1:])):
                errors.append(f"{k}: must grow")
            continue
        if not isinstance(v, (int, float)) or isinstance(v, bool):
            errors.append(f"{k}: not a number")
            continue
        if spec["type"] == "int" and float(v) != int(v):
            errors.append(f"{k}: whole number")
        if not spec["min"] <= v <= spec["max"]:
            errors.append(f"{k}: {spec['min']}..{spec['max']}")
    if errors:
        return errors
    if test_id == "temp_tower":
        if prm["t_start"] == prm["t_end"]:
            errors.append("t_end: equals t_start")
        elif not 2 <= _levels(prm["t_start"], prm["t_end"], prm["t_step"]) <= 16:
            errors.append("t_step: 2..16 levels")
    elif test_id == "flow":
        if prm["f_start"] + 8 * prm["f_step"] > 160:
            errors.append("f_step: the last plate above 160 %")
    elif test_id == "pressure_advance":
        if prm["pa_end"] <= prm["pa_start"]:
            errors.append("pa_end: not above pa_start")
        else:
            n = py_round((prm["pa_end"] - prm["pa_start"]) / prm["pa_step"]) + 1
            if not 3 <= n <= 31:
                errors.append("pa_step: 3..31 lines")
    elif test_id == "retraction":
        if prm["r_start"] + (prm["r_count"] - 1) * prm["r_step"] > 15:
            errors.append("r_step: the last level above 15 mm")
    elif test_id == "max_flow":
        if prm["v_end"] < prm["v_start"] + 4:
            errors.append("v_end: at least 4 mm³/s above v_start")
    elif test_id == "ringing":
        if prm["a_start"] > printer["max_accel"]:
            errors.append("a_start: above the printer's max acceleration")
    return errors


# ---------- помощник результата ----------

_NUM = re.compile(r"[-+]?\d+(?:[.,]\d+)?")


def _numbers(text):
    return [float(s.replace(",", ".")) for s in _NUM.findall(text or "")]


def helper(test_id, text, printer, material, prm):
    """{"ok": bool, "value": str, "unit": str, "note": key} or {"ok": False, "error": key}.

    The note keys are translated by the UI (profiles/ui_text.json, helper_* entries)."""
    info = test_info(test_id)
    if not info["helper"]:
        return {"ok": False, "error": "no_helper"}
    nums = _numbers(text)
    raw = (text or "").strip()
    if not nums:
        return {"ok": False, "error": "need_number"}
    v = nums[0]
    kind = info["helper"]["kind"]
    if kind == "temp":
        return {"ok": True, "value": str(int(py_round(v))), "unit": "°C", "note": "helper_temp"}
    if kind == "flow":
        return {"ok": True, "value": fixed(material["flow"] * v / 100, 3), "unit": "", "note": "helper_flow"}
    if kind == "pa":
        val = v if ("." in raw or "," in raw) else v / 1000
        return {"ok": True, "value": fixed(val, 3), "unit": "", "note": "helper_pa"}
    if kind == "retraction":
        val = v if ("." in raw or "," in raw) else v / 10
        return {"ok": True, "value": trim(val, 2), "unit": "mm", "note": "helper_retraction"}
    if kind == "max_flow":
        return {"ok": True, "value": fixed(v * 0.85, 1), "unit": "mm³/s", "note": "helper_max_flow"}
    if kind == "overhang":
        return {"ok": True, "value": str(int(py_round(90 - v))), "unit": "°", "note": "helper_overhang"}
    if kind == "ringing":
        n = int(py_round(v))
        accels = [prm["a_start"] + prm["a_step"] * i for i in range(prm["a_count"])]
        accels = [a for a in accels if a <= printer["max_accel"]]
        if n < 1 or n > len(accels):
            return {"ok": False, "error": "out_of_range"}
        if n == 1:
            return {"ok": True, "value": str(accels[0] // 2), "unit": "mm/s²", "note": "helper_ringing_first"}
        return {"ok": True, "value": str(accels[n - 2]), "unit": "mm/s²", "note": "helper_ringing"}
    if kind == "tolerance":
        val = v if ("." in raw or "," in raw) else v / 100
        return {"ok": True, "value": fixed(val, 2), "unit": "mm", "note": "helper_tolerance"}
    if kind == "cube":
        if len(nums) < 3:
            return {"ok": False, "error": "need_three"}
        size = prm.get("size", 20)
        dx, dy, dz = (n - size for n in nums[:3])
        if max(abs(dx), abs(dy), abs(dz)) <= 0.1:
            return {"ok": True, "value": "OK", "unit": "", "note": "helper_cube_ok"}
        if max(dx, dy) - min(dx, dy) <= 0.1 and dx * dy > 0:
            avg = (nums[0] + nums[1]) / 2
            return {"ok": True, "value": fixed(material["flow"] * size / avg, 3), "unit": "", "note": "helper_cube_flow"}
        axis = "X" if abs(dx) > abs(dy) else "Y"
        return {"ok": True, "value": axis, "unit": "", "note": "helper_cube_axis"}
    return {"ok": False, "error": "no_helper"}


def summary(res):
    """Time and grams of a generated file, for the cards."""
    minutes = py_round(res.time / 60)
    return {"name": res.name, "minutes": minutes, "grams": fixed(res.grams, 1),
            "lines": len(res.g.lines), "max_z": fixed(res.max_z, 2)}
