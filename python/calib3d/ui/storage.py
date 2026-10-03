"""Where the window keeps its files: settings, window place, the user's own profiles.

%APPDATA%\\Calibrate3dPrinter on Windows (~/.config/calibrate3dprinter elsewhere). With
portable.txt next to the exe, a "data" folder next to it. CALIB3D_HOME overrides both
(the tests use it so they never touch the real profile).
"""
import json
import os
import re
import sys
from pathlib import Path

APP = "Calibrate3dPrinter"


def home() -> Path:
    env = os.environ.get("CALIB3D_HOME")
    if env:
        return Path(env)
    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "portable.txt").exists():
            return exe_dir / "data"
    if os.name == "nt" and os.environ.get("APPDATA"):
        return Path(os.environ["APPDATA"]) / APP
    return Path.home() / ".config" / APP.lower()


def load_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def save_json(path, data) -> bool:
    """Write through a temporary file: a crash in the middle leaves the old file."""
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
        return True
    except OSError:
        return False


def settings_path():
    return home() / "settings.json"


def window_path():
    return home() / "window.json"


def user_dir(kind):
    return home() / "profiles" / kind


def slug(name):
    s = re.sub(r"[^A-Za-z0-9._-]+", "-", name.strip()).strip("-").lower()
    return s or "profile"


def user_profiles(kind):
    out = []
    d = user_dir(kind)
    if d.is_dir():
        for f in sorted(d.glob("*.json")):
            data = load_json(f)
            if isinstance(data, dict) and data.get("id"):
                data["_user"] = True
                out.append(data)
    return out


def save_user_profile(kind, data):
    data = {k: v for k, v in data.items() if not k.startswith("_")}
    pid = "my-" + slug(data.get("name", "profile"))
    data["id"] = pid
    ok = save_json(user_dir(kind) / f"{pid}.json", data)
    return pid if ok else None


def delete_user_profile(kind, pid):
    f = user_dir(kind) / f"{pid}.json"
    try:
        f.unlink()
        return True
    except OSError:
        return False
