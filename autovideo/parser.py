import re
from pathlib import Path

SCENE_KEYS = {"image", "type", "value", "label", "items", "icon", "say"}

DEFAULTS = {
    "voice": "bn-BD-NabanitaNeural",
    "font": "assets/fonts/NotoSansBengali.ttf",
    "music": "",
    "rate": "-5%",
    "pitch": "+0Hz",
    "fps": "24",
}

SCENE_DEFAULTS = {
    "type": "text",
    "image": "",
    "value": "",
    "label": "",
    "items": "",
    "icon": "person",
    "say": "",
}


def parse(path):
    text = Path(path).read_text(encoding="utf-8")
    config = dict(DEFAULTS)
    scenes = []

    for block in re.split(r"\n\s*\n", text.strip()):
        lines = []
        options = {}
        for raw in block.splitlines():
            line = raw.strip()
            if line.startswith("@"):
                key, _, value = line[1:].partition(" ")
                if key in SCENE_KEYS:
                    options[key] = value.strip()
                else:
                    config[key] = value.strip()
            elif line:
                lines.append(line)
        if lines:
            scenes.append({**SCENE_DEFAULTS, **options, "text": " ".join(lines)})

    config["fps"] = int(config["fps"])
    return config, scenes