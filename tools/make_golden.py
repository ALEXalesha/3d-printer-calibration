"""Regenerate tests/golden from reference/calibration.py - into a temporary folder only.

    python tools/make_golden.py          # compare the reference output with tests/golden
    python tools/make_golden.py --write  # and copy it into tests/golden (+ SHA256SUMS)

The reference script writes to a hard-coded personal folder (its OUT constant). It is never
run as is: a copy goes to a temporary folder with OUT replaced, and the copy refuses to run
if the replacement did not happen.
"""
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ROOT / "reference" / "calibration.py"
GOLDEN = ROOT / "tests" / "golden"


def run_reference(out_dir: Path) -> list[Path]:
    src = REFERENCE.read_text(encoding="utf-8")
    lines = src.splitlines(keepends=True)
    hits = [i for i, line in enumerate(lines) if line.startswith("OUT = Path(")]
    if len(hits) != 1:
        raise SystemExit("reference/calibration.py: expected exactly one 'OUT = Path(' line")
    lines[hits[0]] = f"OUT = Path({str(out_dir)!r})\n"
    patched = "".join(lines)
    if repr(str(out_dir)) not in patched or "All_3d" in lines[hits[0]]:
        raise SystemExit("OUT was not replaced - refusing to run the reference")
    script = out_dir.parent / "reference_copy.py"
    script.write_text(patched, encoding="utf-8")
    subprocess.run([sys.executable, str(script)], check=True, stdout=subprocess.DEVNULL)
    return sorted(out_dir.glob("*.gcode"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    write = "--write" in sys.argv
    with tempfile.TemporaryDirectory(prefix="calib3d-golden-") as tmp:
        out = Path(tmp) / "out"
        out.mkdir()
        files = run_reference(out)
        if len(files) != 20:
            print(f"expected 20 files, got {len(files)}")
            return 1
        differ = [f.name for f in files if not (GOLDEN / f.name).exists()
                  or (GOLDEN / f.name).read_bytes() != f.read_bytes()]
        print(f"{len(files)} files, {len(differ)} differ from tests/golden")
        for name in differ:
            print("  ", name)
        if write:
            GOLDEN.mkdir(parents=True, exist_ok=True)
            for f in files:
                shutil.copyfile(f, GOLDEN / f.name)
            sums = "".join(f"{sha256(GOLDEN / f.name)} *{f.name}\n" for f in files)
            (GOLDEN / "SHA256SUMS").write_text(sums, encoding="ascii", newline="\n")
            print("tests/golden updated")
        return 0 if (write or not differ) else 1


if __name__ == "__main__":
    sys.exit(main())
