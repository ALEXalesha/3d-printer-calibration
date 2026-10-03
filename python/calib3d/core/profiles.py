"""Printer and material profiles: shared JSON files read by both editions.

profiles/printers/*.json, profiles/materials/*.json, profiles/firmware.json - the same files
the browser edition gets bundled into web/js/core/data.js (tools/build_data.py).
"""
import copy
import json
import math
import sys
from pathlib import Path


def profiles_dir() -> Path:
    base = getattr(sys, "_MEIPASS", None)  # inside the PyInstaller build
    if base:
        return Path(base) / "profiles"
    return Path(__file__).resolve().parents[3] / "profiles"


def version() -> str:
    base = getattr(sys, "_MEIPASS", None)
    root = Path(base) if base else Path(__file__).resolve().parents[3]
    return (root / "VERSION").read_text(encoding="utf-8").strip()


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


_cache = {}


def _load(name):
    if name not in _cache:
        d = profiles_dir()
        if name == "printers":
            _cache[name] = sorted((_read(p) for p in (d / "printers").glob("*.json")),
                                  key=lambda p: (not p.get("verified"), p["name"].lower()))
        elif name == "materials":
            order = ["pla", "petg", "abs", "asa", "tpu"]
            items = [_read(p) for p in (d / "materials").glob("*.json")]
            _cache[name] = sorted(items, key=lambda m: order.index(m["id"]) if m["id"] in order else 99)
        else:
            _cache[name] = _read(d / f"{name}.json")
    return _cache[name]


def printers():
    return copy.deepcopy(_load("printers"))


def materials():
    return copy.deepcopy(_load("materials"))


def firmware():
    return copy.deepcopy(_load("firmware"))


def schema():
    return _load("schema")


def printer(pid):
    for p in _load("printers"):
        if p["id"] == pid:
            return copy.deepcopy(p)
    raise KeyError(pid)


def material(mid):
    for m in _load("materials"):
        if m["id"] == mid:
            return copy.deepcopy(m)
    raise KeyError(mid)


def _get(d, path):
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None, False
        cur = cur[part]
    return cur, True


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _check_field(d, spec, errors, required=True):
    path, kind = spec[0], spec[1]
    v, present = _get(d, path)
    if not present:
        if required:
            errors.append(f"{path}: missing")
        return
    if kind == "str":
        ok = isinstance(v, str) and v.strip() != ""
    elif kind == "bool":
        ok = isinstance(v, bool)
    elif kind in ("num", "int"):
        ok = _num(v) and (kind == "num" or float(v).is_integer())
        if ok and len(spec) > 2 and not (spec[2] <= v <= spec[3]):
            errors.append(f"{path}: {v} outside {spec[2]}..{spec[3]}")
            return
    elif kind == "enum":
        ok = v in spec[2]
    elif kind == "lines":
        ok = isinstance(v, list) and len(v) > 0 and all(isinstance(s, str) for s in v)
    elif kind == "list":
        ok = isinstance(v, list) and len(v) == 2 and all(_num(x) and spec[2] <= x <= spec[3] for x in v) and v[0] < v[1]
    elif kind == "flags":
        ok = isinstance(v, dict) and all(isinstance(x, bool) for x in v.values())
    elif kind == "state":
        ok = isinstance(v, dict) and all(_num(v.get(k)) for k in ("x", "y", "z", "e", "time"))
    elif kind == "overrides":
        ok = isinstance(v, dict) and all(isinstance(x, (str, list)) or x is None for x in v.values())
    else:
        ok = False
    if not ok:
        errors.append(f"{path}: bad value {v!r}")


def validate_printer(p):
    """Problems of a printer profile, empty list - all good."""
    errors = []
    if not isinstance(p, dict):
        return ["not an object"]
    for spec in schema()["printer"]:
        _check_field(p, spec, errors)
    for spec in schema()["printer_optional"]:
        _check_field(p, spec, errors, required=False)
    if not errors and p["default_accel"] > p["max_accel"]:
        errors.append("default_accel: above max_accel")
    if not errors and p["bed"]["shape"] == "round" and p["bed"]["origin"] != "center":
        errors.append("bed.origin: a round bed has its origin in the centre")
    return errors


def validate_material(m):
    errors = []
    if not isinstance(m, dict):
        return ["not an object"]
    for spec in schema()["material"]:
        _check_field(m, spec, errors)
    if not errors:
        t = m["tower"]
        if t["start"] == t["end"]:
            errors.append("tower: start equals end")
        elif abs(t["start"] - t["end"]) / t["step"] > 15:
            errors.append("tower: more than 16 levels")
    return errors
