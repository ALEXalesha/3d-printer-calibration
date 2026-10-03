"""Mutation check: break the core on purpose and make sure the tests go red.

    python tools/mutate.py            # all Python mutations
    python tools/mutate.py --js       # all JavaScript mutations (node:test)
    python tools/mutate.py golden-e   # one by name

Each mutation is applied to a copy of the project in a temporary folder (python/,
profiles/, web/js/core/, tests/, VERSION), never to the working files. A mutation that
leaves the tests green is a hole in the tests: the script lists it and exits with 1.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY_CORE = "python/calib3d/core/"
JS_CORE = "web/js/core/"

# name, file, old text, new text, tests to run (pytest -k / node test files)
PY = [
    ("golden-e-sign", PY_CORE + "generator.py", 'E{fixed(e, 5)}', 'E{fixed(-e, 5)}', "test_golden"),
    ("golden-retract", PY_CORE + "generator.py", 'self.out(f"G1 E-{fixed(self.retract_len, 2)}', 'self.out(f"G1 E-{fixed(self.retract_len * 1.01, 2)}', "test_golden"),
    ("golden-tower-temp", PY_CORE + "generator.py", '        g.out(f"M104 S{t}")\n', '', "test_golden"),
    ("golden-pa-command", PY_CORE + "generator.py", 'self.ctx.fw["pressure_advance"]', 'self.ctx.fw["fan"]', "test_golden"),
    ("golden-slow-layer", PY_CORE + "generator.py", "if 0 < dt < min_time:", "if 0 < dt < min_time * 0.5:", "test_golden"),
    ("golden-hypot", PY_CORE + "num.py", "h += (csum - 1.0 + (frac1 + frac2)) / (2.0 * h)", "pass", "test_num or test_golden"),
    ("golden-fan", PY_CORE + "generator.py", 'str(py_round(255 * frac))', 'str(int(255 * frac))', "test_golden"),
]
JS = []


def load_extra():
    """Mutation lists grow with the project: tools/mutations.json adds to the two above."""
    path = ROOT / "tools" / "mutations.json"
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        PY.extend(tuple(m) for m in data.get("py", []))
        JS.extend(tuple(m) for m in data.get("js", []))


def copy_project(dst: Path):
    for part in ("python", "profiles", "tests", "web/js", "web/css", "web/index.html", "assets", "VERSION",
                 "pytest.ini", "package.json", "README.md", "README.ru.md", "LICENSE"):
        src = ROOT / part
        if not src.exists():
            continue
        if src.is_dir():
            shutil.copytree(src, dst / part, ignore=shutil.ignore_patterns("__pycache__", "golden_out"))
        else:
            (dst / part).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst / part)
    nm = ROOT / "node_modules"
    if nm.exists() and not (dst / "node_modules").exists():
        # a junction, not a copy: node_modules is big and only read
        subprocess.run(["cmd", "/c", "mklink", "/J", str(dst / "node_modules"), str(nm)],
                       check=True, stdout=subprocess.DEVNULL)


def run_one(m, js):
    name, file, old, new, tests = m
    with tempfile.TemporaryDirectory(prefix="calib3d-mut-") as tmp:
        tmp = Path(tmp)
        copy_project(tmp)
        target = tmp / file
        src = target.read_text(encoding="utf-8")
        if old not in src:
            return name, "NOT FOUND"
        target.write_text(src.replace(old, new, 1), encoding="utf-8", newline="\n")
        env = dict(os.environ, CALIB3D_PYROOT=str(tmp / "python"), HYPOTHESIS_PROFILE="quick")
        if js:
            files = [str(tmp / "tests" / "js" / f) for f in tests.split()]
            cmd = ["node", "--test", "--test-concurrency=1"] + files
        else:
            cmd = [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:randomly", "-k", tests, str(tmp / "tests" / "py")]
        try:
            r = subprocess.run(cmd, cwd=tmp, env=env, capture_output=True, text=True, timeout=900)
            caught = r.returncode != 0
            if name == "control" and caught:
                print((r.stdout + r.stderr)[-3000:])
        except subprocess.TimeoutExpired:
            caught = True
        finally:
            nm = tmp / "node_modules"
            if nm.exists():
                os.rmdir(nm)  # removes the junction only, not the real folder
        return name, "caught" if caught else "SURVIVED"


def main():
    load_extra()
    js = "--js" in sys.argv
    names = [a for a in sys.argv[1:] if not a.startswith("--")]
    pool = [m for m in (JS if js else PY) if not names or m[0] in names]
    # Control: the untouched copy must be green, otherwise "caught" means nothing.
    if pool:
        first = pool[0]
        control = ("control", first[1], first[2], first[2], first[4])
        status = run_one(control, js)[1]
        if status != "SURVIVED":
            print("control run failed on an untouched copy:", "pattern not found" if status == "NOT FOUND" else "tests are red")
            return 2
        print("control   untouched copy is green")
    bad = 0
    for m in pool:
        name, status = run_one(m, js)
        print(f"{status:9} {name}", flush=True)
        bad += status != "caught"
    print(f"{len(pool) - bad}/{len(pool)} mutations caught")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
