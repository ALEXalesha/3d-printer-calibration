import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, os.environ.get("CALIB3D_PYROOT") or str(ROOT / "python"))

# Qt without a screen: never a visible window during tests. Fonts from Windows, so
# text on test screenshots looks like in the real window.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_fonts = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
if os.path.isdir(_fonts):
    os.environ.setdefault("QT_QPA_FONTDIR", _fonts)

from hypothesis import settings  # noqa: E402

settings.register_profile("default", max_examples=400, deadline=None)
settings.register_profile("quick", max_examples=60, deadline=None)
settings.register_profile("thorough", max_examples=4000, deadline=None)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "default"))


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _own_home(tmp_path, monkeypatch):
    """Settings, window place and own profiles go to a temporary folder, never the real one."""
    monkeypatch.setenv("CALIB3D_HOME", str(tmp_path / "home"))
    return tmp_path / "home"


_app = None


@pytest.fixture
def qapp():
    global _app
    from PySide6.QtWidgets import QApplication
    _app = QApplication.instance() or QApplication([])
    return _app
