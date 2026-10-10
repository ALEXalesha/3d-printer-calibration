"""The two installers live side by side on one machine and must not touch each other.

The 1.0.0 previews named the Python edition exactly like the Electron one: both put a
"Calibrate 3D Printer" shortcut on the desktop, so the second install overwrote the first and
uninstalling either removed the other's shortcut. InstallAll also tells them apart by the
name in "Apps" ("Calibrate 3D Printer 1.0.0" is Electron).
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _nsi_define(name):
    text = (ROOT / "tools" / "installer_py.nsi").read_text(encoding="utf-8")
    m = re.search(rf'^!define {name} "([^"]+)"', text, re.MULTILINE)
    assert m, name
    return m.group(1)


def test_python_installer_has_its_own_names():
    build = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["build"]
    electron_names = {build["productName"], build["nsis"]["shortcutName"]}
    title = _nsi_define("TITLE")
    assert title not in electron_names
    assert "Python" in title
    # Electron installs into Programs\<productName>; the Python edition into Programs\<APP>.
    assert _nsi_define("APP").lower() != build["productName"].lower()


def test_installall_patterns_do_not_mix():
    build = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    electron_entry = f'{build["build"]["productName"]} {build["version"]}'   # what NSIS of electron-builder writes
    python_entry = _nsi_define("TITLE")
    electron_re = re.compile(r"^Calibrate 3D Printer [\d.]+$")
    python_re = re.compile(r"^Calibrate 3D Printer \(Python\)$")
    assert electron_re.match(electron_entry) and not electron_re.match(python_entry)
    assert python_re.match(python_entry) and not python_re.match(electron_entry)
