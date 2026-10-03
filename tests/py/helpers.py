import importlib.util
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def reference():
    """reference/calibration.py as a module (importing it writes nothing)."""
    spec = importlib.util.spec_from_file_location("reference_calibration", ROOT / "reference" / "calibration.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
