"""Interface strings (profiles/ui_text.json), shared with the web page."""
import json

from ..core import profiles

_TEXT = None
LANGS = ["ru", "en"]


def table():
    global _TEXT
    if _TEXT is None:
        _TEXT = json.loads((profiles.profiles_dir() / "ui_text.json").read_text(encoding="utf-8"))
    return _TEXT


def tr(key, lang, **values):
    entry = table().get(key)
    s = key if entry is None else entry.get(lang) or entry.get("en") or key
    for k, v in values.items():
        s = s.replace("{" + k + "}", str(v))
    return s


def default_lang():
    from PySide6.QtCore import QLocale
    return "ru" if QLocale.system().language() == QLocale.Language.Russian else "en"
