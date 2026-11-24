import re
from pathlib import Path

SCENE_KEYS = {"image", "type", "value", "label", "items", "icon", "say", "audio"}

DEFAULTS = {
    "provider": "edge",
    "voice": "bn-BD-NabanitaNeural",
    "rate": "-5%",
    "pitch": "+0Hz",
    "gemini_voice": "Sulafat",
    "style": "Read this in natural, warm, conversational Bangla, like a friendly presenter",
    "tts_model": "gemini-2.5-flash-preview-tts",
    "font": "assets/fonts/NotoSansBengali.ttf",
    "music": "",
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
    "audio": "",
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