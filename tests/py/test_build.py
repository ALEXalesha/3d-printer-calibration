"""The built exe (tools/build_py.py) runs its self-test without a window. Skipped before a build."""
import subprocess
import time
from pathlib import Path

import pytest

EXE = Path(__file__).resolve().parents[2] / "dist" / "python" / "Calibrate3dPrinter" / "Calibrate3dPrinter.exe"


@pytest.mark.skipif(not EXE.exists(), reason="no build in dist/python")
def test_exe_self_test(tmp_path):
    out = tmp_path / "self-test.txt"
    proc = subprocess.Popen([str(EXE), f"--self-test={out}"])
    try:
        rc = proc.wait(timeout=180)
    finally:
        if proc.poll() is None:
            proc.kill()
    end = time.monotonic() + 10
    while not out.exists() and time.monotonic() < end:
        time.sleep(0.2)
    text = out.read_text(encoding="utf-8")
    assert rc == 0 and text.rstrip().endswith("SELF-TEST OK"), text[-500:]
