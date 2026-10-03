"""Bundle profiles/*.json and VERSION into web/js/core/data.js.

The page must open from a file (file:// cannot fetch JSON) and from GitHub Pages, so the
shared JSON files travel inside one script. tests/js/data.test.js checks that data.js is
up to date with the JSON files.

    python tools/build_data.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILES = ROOT / "profiles"
OUT = ROOT / "web" / "js" / "core" / "data.js"


def read(p):
    return json.loads(p.read_text(encoding="utf-8"))


def bundle():
    order = ["pla", "petg", "abs", "asa", "tpu"]
    mats = [read(p) for p in sorted((PROFILES / "materials").glob("*.json"))]
    mats.sort(key=lambda m: order.index(m["id"]) if m["id"] in order else 99)
    printers = [read(p) for p in sorted((PROFILES / "printers").glob("*.json"))]
    printers.sort(key=lambda p: (not p.get("verified"), p["name"].lower()))
    return {
        "version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        "printers": printers,
        "materials": mats,
        "firmware": read(PROFILES / "firmware.json"),
        "schema": read(PROFILES / "schema.json"),
        "tables": read(PROFILES / "tables.json"),
        "gcode_text": read(PROFILES / "gcode_text.json"),
        "tests": read(PROFILES / "tests.json")["tests"],
        "ui_text": read(PROFILES / "ui_text.json"),
    }


def render():
    body = json.dumps(bundle(), ensure_ascii=False, indent=1)
    return ("// Made by tools/build_data.py from profiles/*.json and VERSION - do not edit by hand.\n"
            "(function () {\n"
            "  'use strict';\n"
            "  const root = typeof globalThis !== 'undefined' ? globalThis : window;\n"
            "  const C3D = root.C3D || (root.C3D = {});\n"
            f"  C3D.data = {body};\n"
            "  if (typeof module === 'object' && module.exports) module.exports = C3D.data;\n"
            "})();\n")


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(), encoding="utf-8", newline="\n")
    print(OUT)
