"""Local only (plan task 11): start code of real ElegooSlicer prints vs the Centauri Carbon
profile. Runs when CALIB3D_REAL_GCODE points at a folder of G-code files; the files are
only read and never copied into the repository (they hold personal paths and names).

    CALIB3D_REAL_GCODE=<folder> python -m pytest tests/py/test_real_files.py -q -s
"""
import os
import re
from pathlib import Path

import pytest

from calib3d.core import generator as G
from calib3d.core import importer as I
from calib3d.core import profiles as P
from calib3d.core import templates as T

FOLDER = os.environ.get("CALIB3D_REAL_GCODE")
REFERENCE_NAMES = re.compile(r"^ECC_0\.4_(FirstLayer|TempTower|Flow|PressureAdvance_Lines|Retraction|MaxFlow|"
                             r"OverhangBridge|Ringing|Tolerance|Cube20)_")
pytestmark = pytest.mark.skipif(not FOLDER or not Path(FOLDER).is_dir(), reason="CALIB3D_REAL_GCODE not set")


def centauri_files(limit=12):
    out = []
    for f in sorted(Path(FOLDER).glob("*.gcode"), key=lambda p: p.stat().st_mtime, reverse=True):
        if REFERENCE_NAMES.match(f.name):
            continue
        with f.open(encoding="utf-8", errors="replace") as fh:
            head = fh.read(4000)
        if "ElegooSlicer" in head:
            out.append(f)
        if len(out) >= limit:
            break
    return out


def commands(lines):
    out = []
    for line in lines:
        code = line.split(";", 1)[0].strip()
        if code and not code.startswith(("M73", "EXCLUDE_OBJECT")):
            out.append(re.sub(r"\s+", " ", code))
    return out


def test_real_start_code_matches_the_profile():
    files = centauri_files()
    assert files, "no ElegooSlicer files in the folder"
    cc = P.printer("elegoo-centauri-carbon")
    same, report = 0, []
    for f in files:
        r = I.parse(f.read_text(encoding="utf-8", errors="replace"), f.name)
        if r["printer"].get("name") != "Elegoo Centauri Carbon":
            continue
        base = P.material("petg" if r["material"].get("type") == "PETG" else "pla")
        printer, material = I.to_profiles(r, cc, base)
        ctx = G.Ctx(cc, material)
        values, flags = G.template_values(ctx, material["first_layer_temp"], "t", 100, 10.0)
        ours, _ = T.expand(cc["start_gcode"], values, flags)
        theirs, unknown = T.expand(r["start_gcode"], values, flags)
        assert unknown == [], (f.name, unknown)
        a, b = commands(ours), commands(theirs)
        if a == b:
            same += 1
        else:
            extra = [c for c in b if c not in a]
            lost = [c for c in a if c not in b]
            report.append((f.name[:40], material["type"], extra[:4], lost[:4]))
        # the printer data in the header is the profile's
        assert printer["bed"]["x"] == 256.0 and printer["nozzle"] == 0.4 and printer["firmware"] == "klipper"
    print(f"\n{same} of {same + len(report)} real Centauri Carbon start codes match the profile command for command")
    for row in report:
        print("  differs:", row)
    assert same >= (same + len(report)) // 2
