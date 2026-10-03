"""The equality law: the JavaScript core gives exactly what the Python core gives.

Cases go to node (tests/js/equality_runner.js) in one batch and come back as JSON:
- G-code on the matrix 3 firmwares x 3 nozzles x 5 materials x 10 tests (SHA-256 of the
  text, name, time and grams), plus random valid settings over all printer profiles;
- the G-code check on files with injected faults; the importer on the six slicer samples
  and on cut and random variants; the result helper; parameter and profile validation;
- the number helpers on tens of thousands of values, exact halves included.
"""
import copy
import hashlib
import json
import random
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from calib3d.core import check as C
from calib3d.core import generator as G
from calib3d.core import importer as I
from calib3d.core import num as N
from calib3d.core import params as PR
from calib3d.core import preview as PV
from calib3d.core import profiles as P

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "tests" / "js" / "equality_runner.js"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node not installed")


def run_js(cases, tmp_path):
    f = tmp_path / "cases.json"
    f.write_text(json.dumps(cases), encoding="utf-8")
    r = subprocess.run([NODE, str(RUNNER), str(f)], capture_output=True, text=True, encoding="utf-8", timeout=1200)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout)


def py_gen(c):
    try:
        r = G.generate(c["printer"], c["material"], c["test"], c.get("params"), c["lang"])
    except G.DoesNotFit:
        return {"error": "does_not_fit"}
    except G.TemplateError:
        return {"error": "template"}
    row = {"name": r.name, "sha": hashlib.sha256(r.text.encode("utf-8")).hexdigest(), "lines": len(r.g.lines),
           "summary": PR.summary(r)}
    if c.get("check"):
        row["problems"] = C.check_result(r, c["test"])
    if c.get("preview"):
        p = PV.preview_data(r)

        def total(lst):
            a = 0.0
            for s in lst:
                a = a + s[0] + 2 * s[1] + 3 * s[2] + 4 * s[3]
            return a
        row["preview"] = [len(p["top"]), len(p["front"]) if p["front"] is not None else -1, N.fixed(total(p["top"]), 3),
                          N.fixed(total(p["front"]), 3) if p["front"] is not None else ""]
    return row


def matrix_cases():
    cases = []
    for pid in ("generic-klipper", "generic-marlin", "generic-rrf"):
        for nz in (0.2, 0.4, 0.6):
            for m in P.materials():
                for k, tid in enumerate(G.TEST_IDS):
                    p = P.printer(pid)
                    p["nozzle"] = nz
                    cases.append({"kind": "gen", "printer": p, "material": m, "test": tid, "params": None,
                                  "lang": "en" if k % 2 else "ru", "check": k % 3 == 0, "preview": k % 4 == 0})
    return cases


def random_cases(seed, n):
    rnd = random.Random(seed)
    printers, mats = P.printers(), P.materials()
    cases = []
    while len(cases) < n:
        p = copy.deepcopy(rnd.choice(printers))
        m = copy.deepcopy(rnd.choice(mats))
        p["nozzle"] = rnd.choice([0.25, 0.3, 0.4, 0.5, 0.6, 0.8])
        p["filament_diameter"] = rnd.choice([1.75, 1.75, 2.85])
        p["retract"]["length"] = round(rnd.uniform(0.2, 6.0), 2)
        p["retract"]["z_hop"] = rnd.choice([0.0, 0.2, 0.4, 0.6])
        p["travel_speed"] = float(rnd.choice([120, 150, 200, 250, 300]))
        m["flow"] = round(rnd.uniform(0.9, 1.05), 3)
        m["mvs"] = round(rnd.uniform(3, 30), 1)
        m["min_layer_time"] = float(rnd.choice([0, 3, 5, 8, 12]))
        m["fan"] = round(rnd.uniform(0, 1), 2)
        m["first_layer_temp"] = m["nozzle_temp"] + rnd.choice([0, 5])
        tid = rnd.choice(G.TEST_IDS)
        prm = G.default_params(tid, m)
        if tid == "temp_tower":
            prm = {"t_start": m["tower"]["start"], "t_end": m["tower"]["start"] - 5 * rnd.randint(1, 8), "t_step": 5}
            m["tower"] = {"start": prm["t_start"], "end": prm["t_end"], "step": 5}
        elif tid == "pressure_advance":
            st = rnd.choice([0.002, 0.005, 0.01])
            prm = {"pa_start": rnd.choice([0.0, 0.01]), "pa_end": 0.0, "pa_step": st}
            prm["pa_end"] = round(prm["pa_start"] + st * rnd.randint(3, 25), 3)
        elif tid == "retraction":
            prm = {"r_start": rnd.choice([0.1, 0.2, 0.5, 1.0]), "r_step": rnd.choice([0.1, 0.2, 0.5]), "r_count": rnd.randint(2, 10)}
        elif tid == "ringing":
            prm = {"a_start": rnd.choice([500, 1000, 2000]), "a_step": rnd.choice([500, 1000, 1500]), "a_count": rnd.randint(2, 14)}
        elif tid == "tolerance":
            prm = {"gaps": sorted(rnd.sample([0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.5], rnd.randint(2, 7)))}
        elif tid == "cube":
            prm = {"size": rnd.randint(10, 40)}
        elif tid == "flow":
            prm = {"f_start": rnd.randint(70, 95), "f_step": rnd.randint(1, 6)}
        elif tid == "max_flow":
            prm = {"v_start": float(rnd.randint(2, 10)), "v_end": float(rnd.randint(16, 40))}
        if P.validate_printer(p) or P.validate_material(m) or PR.validate(tid, prm, p, m):
            continue
        cases.append({"kind": "gen", "printer": p, "material": m, "test": tid, "params": prm,
                      "lang": rnd.choice(["ru", "en"]), "check": True, "preview": True})
    return cases


def test_generation_matrix_and_random(tmp_path):
    cases = matrix_cases() + random_cases(2026, 120)
    js = run_js(cases, tmp_path)
    assert len(js) == len(cases)
    bad = []
    for c, j in zip(cases, js):
        py = py_gen(c)
        if py != j:
            bad.append((c["printer"]["id"], c["printer"]["nozzle"], c["material"]["id"], c["test"], py.get("name"), j.get("name"),
                        {k: (py.get(k), j.get(k)) for k in set(py) | set(j) if py.get(k) != j.get(k)}))
    assert not bad, f"{len(bad)} of {len(cases)} differ, first: {bad[:3]}"


def test_check_on_faulty_files(tmp_path):
    rnd = random.Random(7)
    cases = []
    for pid, mid, tid in (("elegoo-centauri-carbon", "petg", "cube"), ("generic-marlin", "pla", "retraction"),
                          ("generic-rrf", "abs", "flow"), ("generic-delta-klipper", "tpu", "tolerance")):
        r = G.generate(P.printer(pid), P.material(mid), tid)
        lines = r.text.split("\n")
        body = list(range(r.g.body_start, r.g.body_end))
        faults = ["G1 X400.000 Y10.000 E0.5 F3000", "M900 K0.1", "SET_PRESSURE_ADVANCE ADVANCE=0.1", "M572 D0 S0.1",
                  "M104 S500", "M140 S10", "G1 Z500 F600", "M204 S999999", "{left_over}", "G1 E-0.80 F1800", ";Z:0.01",
                  "G1 X10 Y10 E-1 F1200", "SET_VELOCITY_LIMIT ACCEL=999999"]
        cases.append({"kind": "check", "text": r.text, "printer": P.printer(pid), "material": P.material(mid), "test": tid,
                      "body_start": r.g.body_start, "body_end": r.g.body_end, "max_z": r.max_z})
        for _ in range(12):
            ls = list(lines)
            for _k in range(rnd.randint(1, 3)):
                i = rnd.choice(body)
                if rnd.random() < 0.5:
                    ls[i] = rnd.choice(faults)
                else:
                    ls[i] = re.sub(r"F\d+", "F" + str(rnd.choice([100, 99999])), ls[i])
            cases.append({"kind": "check", "text": "\n".join(ls), "printer": P.printer(pid), "material": P.material(mid),
                          "test": tid, "body_start": r.g.body_start, "body_end": r.g.body_end, "max_z": r.max_z})
    js = run_js(cases, tmp_path)
    for c, j in zip(cases, js):
        py = C.check(c["text"], c["printer"], c["material"], c["test"], c["body_start"], c["body_end"], c["max_z"])
        assert py == j["problems"]
    assert sum(1 for j in js if j["problems"]) >= 40


def test_importer(tmp_path):
    rnd = random.Random(11)
    texts = []
    for f in sorted((ROOT / "tests" / "import").glob("*.gcode")):
        t = f.read_text(encoding="utf-8")
        texts.append((f.name, t))
        lines = t.split("\n")
        for _ in range(6):
            ls = [x for x in lines if rnd.random() > 0.15]
            texts.append((f.name, "\n".join(ls)))
        texts.append((f.name, t.replace("\n", "\r\n")))
    alphabet = "G1 XYZEF0123456789.;=-\n;LAYER_CHANGE\n; key = value\nM104 S200\n"
    for _ in range(30):
        texts.append(("rand", "".join(rnd.choice(alphabet) for _ in range(rnd.randint(0, 300)))))
    gen = G.generate(P.printer("generic-klipper"), P.material("pla"), "first_layer").text
    texts.append(("ours.gcode", gen))
    cases = [{"kind": "import", "text": t, "file": n} for n, t in texts]
    js = run_js(cases, tmp_path)
    for (n, t), j in zip(texts, js):
        assert I.parse(t, n) == j, n


def test_helper_and_validation(tmp_path):
    cc, m = P.printer("elegoo-centauri-carbon"), P.material("pla")
    inputs = ["", "abc", "0", "5", "24", "024", "0.035", "1,2", "104", "-3", "12", "60", "19.7 19.7 19.9",
              "20 19.6 20", "20.02 19.98 20.05", "300"]
    cases = [{"kind": "helper", "test": t, "text": x, "printer": cc, "material": m, "params": G.default_params(t, m)}
             for t in G.TEST_IDS for x in inputs]
    rnd = random.Random(3)
    vcases = []
    for _ in range(200):
        t = rnd.choice(G.TEST_IDS)
        prm = G.default_params(t, m)
        for k in list(prm):
            if rnd.random() < 0.5:
                prm[k] = rnd.choice([0, 1, -5, 2.5, 1000, 0.001, "x", None, [0.1, 0.2], [0.3, 0.1]])
        vcases.append({"kind": "validate", "test": t, "params": prm, "printer": cc, "material": m})
    for _ in range(60):
        p = P.printer(rnd.choice([x["id"] for x in P.printers()]))
        mat = P.material(rnd.choice([x["id"] for x in P.materials()]))
        key = rnd.choice(["nozzle", "max_accel", "firmware", "bed", "start_gcode"])
        p[key] = rnd.choice([0, 0.4, "klipper", "x", [], {"x": 1}, 12000])
        mat[rnd.choice(["bed", "flow", "tower"])] = rnd.choice([0, 1.2, 500, "x"])
        vcases.append({"kind": "validate", "test": "cube", "params": {"size": 20}, "printer": p, "material": mat})
    js = run_js(cases + vcases, tmp_path)
    for c, j in zip(cases, js[:len(cases)]):
        assert PR.helper(c["test"], c["text"], c["printer"], c["material"], c["params"]) == j, (c["test"], c["text"])
    for c, j in zip(vcases, js[len(cases):]):
        try:
            errs = PR.validate(c["test"], c["params"], c["printer"], c["material"])
        except TypeError:
            errs = None
        if errs is not None:
            assert errs == j["errors"], c
        assert P.validate_printer(c["printer"]) == j["printer"]
        assert P.validate_material(c["material"]) == j["material"]


def test_number_helpers(tmp_path):
    rnd = random.Random(5)
    values = []
    for _ in range(20000):
        d = rnd.randint(0, 5)
        kind = rnd.random()
        if kind < 0.3:      # exact halves: where toFixed and Python disagree
            x = rnd.randint(-10**5, 10**5) / 2 ** (d + 1)
        elif kind < 0.6:
            x = round(rnd.uniform(-300, 300), rnd.randint(0, 6))
        else:
            x = rnd.uniform(-1e4, 1e4)
        values.append([x, d])
    values += [[0.125, 2], [0.375, 2], [2.5, 0], [3.5, 0], [-0.0, 2], [-0.0004, 3], [1e-7, 3], [255 * 0.5, 0]]
    pairs = [[rnd.uniform(-300, 300), rnd.uniform(-300, 300)] for _ in range(20000)]
    pairs += [[0.0, 0.0], [3.0, 4.0], [1e-310, 0.0], [5e-324, 5e-324]]
    js = run_js([{"kind": "num", "values": values, "pairs": pairs}], tmp_path)[0]
    assert js["fixed"] == [N.fixed(x, d) for x, d in values]
    assert js["round"] == [N.py_round(x) for x, _ in values]
    assert js["repr"] == [N.py_repr(x) for x, _ in values]
    assert js["hypot"] == [N.hypot(a, b) for a, b in pairs]
