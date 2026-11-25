import json
import re
from pathlib import Path

LATIN = re.compile(r"[A-Za-z]")


def load_lexicon(path):
    if not path or not Path(path).exists():
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {str(key): str(value) for key, value in data.items()}


def _pattern(key):
    escaped = re.escape(key)
    if LATIN.search(key):
        return re.compile(rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])", re.IGNORECASE)
    return re.compile(rf"(?<![\u0980-\u09ff]){escaped}(?![\u0980-\u09ff])")


def apply_lexicon(text, lexicon):
    for key in sorted(lexicon, key=len, reverse=True):
        replacement = lexicon[key]
        text = _pattern(key).sub(lambda _match, value=replacement: value, text)
    return text