"""Backend language helpers. Supported: English, Kannada, Hindi, Telugu.

Translatable database text is stored as {"en": …, "kn": …, "hi": …, "te": …}. A missing translation falls back
to English and is logged once per (field, language) so gaps can be filled — never silently.
"""
from __future__ import annotations

import logging
from typing import Any

LANGS = ("en", "kn", "hi", "te")
LANG_NAMES = {"en": "English", "kn": "Kannada", "hi": "Hindi", "te": "Telugu"}

log = logging.getLogger("samvaad.i18n")
_missing_logged: set[tuple[str, str]] = set()
missing_counter: dict[str, int] = {}


def norm_lang(lang: str | None) -> str:
    return lang if lang in LANGS else "en"


def tr(value: Any, lang: str | None, field: str = "text") -> Any:
    """Pick `lang` from a {lang: value} dict; fall back to English (logged), then any language."""
    if not isinstance(value, dict):
        return value
    lang = norm_lang(lang)
    if value.get(lang) not in (None, "", []):
        return value[lang]
    key = (field, lang)
    missing_counter[lang] = missing_counter.get(lang, 0) + 1
    if key not in _missing_logged:
        _missing_logged.add(key)
        log.warning("missing %s translation for %s; using English", lang, field)
    if value.get("en") not in (None, "", []):
        return value["en"]
    return next((v for v in value.values() if v not in (None, "", [])), None)


def detect_script(text: str) -> str | None:
    """Which supported language a message is written in, from its script.
    Latin script returns None (it could be English or transliterated Kannada/Hindi/Telugu)."""
    counts = {"kn": 0, "hi": 0, "te": 0}
    for ch in text:
        o = ord(ch)
        if 0x0C80 <= o <= 0x0CFF:
            counts["kn"] += 1
        elif 0x0900 <= o <= 0x097F:
            counts["hi"] += 1
        elif 0x0C00 <= o <= 0x0C7F:
            counts["te"] += 1
    best = max(counts, key=lambda k: counts[k])
    return best if counts[best] >= 2 else None
