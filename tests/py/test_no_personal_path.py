"""No personal disk path of the author in the repository files.

The repository goes to GitHub as an open project. A path to the author's folder on his
disk (in examples, docs and the reference script) carries his name. The publish script
replaces such a path in the whole history too, but this check catches it earlier: on the
very commit that brings it, and in CI as well.

The path is searched in any spelling: forward or back slash, a doubled back slash (as in
JSON and Python strings), any case. It is not written here in one piece - otherwise the
check would find itself.
"""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PERSONAL = re.compile(r"drive[\\/]+" + "alexey", re.IGNORECASE)


def _tracked_files():
    try:
        out = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True,
                             check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        # No git (a source archive): every file but the service folders.
        skip = {".git", "build", "dist", "node_modules", "__pycache__", ".venv", ".ci-venv"}
        return [p for p in ROOT.rglob("*")
                if p.is_file() and not skip.intersection(p.relative_to(ROOT).parts)]
    return [ROOT / name for name in out.decode("utf-8").split("\0") if name]


def test_no_personal_path_in_files():
    found = []
    for path in _tracked_files():
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"\0" in data[:8192]:
            continue  # a binary file
        text = data.decode("utf-8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            if PERSONAL.search(line):
                found.append(f"{path.relative_to(ROOT).as_posix()}:{n}")
    assert not found, "the author's personal path in files: " + ", ".join(found)


def test_the_pattern_catches_every_spelling():
    head, tail = "Drive", "Alexey"
    for s in (f"C:\\{head}\\{tail}\\x", f"c:/{head.lower()}/{tail.lower()}", f"C:\\\\{head}\\\\{tail}",
              f"/c/{head}/{tail}/"):
        assert PERSONAL.search(s), s
    assert not PERSONAL.search("C:\\Projects\\Calibrate3dPrinter")
