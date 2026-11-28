import json
import re
from dataclasses import dataclass
from pathlib import Path

from .lexicon import load_lexicon
from .speech import prepare_speech

TYPES = {"text", "counter", "bullets"}
PROVIDERS = {"edge", "gemini"}
MAX_WORDS = 25
MAX_ITEMS = 3
MAX_ITEM_CHARS = 40
MAX_RUN = 3
MAX_TEXT_RUN = 2
WORDS_PER_SECOND = 2.3
MIN_SCENE_SECONDS = 2.0
PAD_SECONDS = 0.6


@dataclass
class Issue:
    level: str
    scene: int
    message: str

    def __str__(self):
        where = f"scene {self.scene}" if self.scene else "config"
        return f"[{self.level}] {where}: {self.message}"


def spoken(scene):
    return scene["say"] or scene["text"]


def estimate_seconds(scenes):
    total = 0.0
    for scene in scenes:
        words = len(spoken(scene).split())
        total += max(words / WORDS_PER_SECOND, MIN_SCENE_SECONDS) + PAD_SECONDS
    return total


def validate(config, scenes):
    issues = []

    def add(level, scene, message):
        issues.append(Issue(level, scene, message))

    if not scenes:
        add("error", 0, "no scenes found")
        return issues

    if config["provider"] not in PROVIDERS:
        add("error", 0, f"unknown provider '{config['provider']}'")
    if not Path(config["font"]).exists():
        add("error", 0, f"font not found: {config['font']}")
    if config["music"] and not Path(config["music"]).exists():
        add("error", 0, f"music file not found: {config['music']}")

    try:
        lexicon = load_lexicon(config.get("lexicon", ""))
    except (json.JSONDecodeError, AttributeError):
        add("error", 0, f"lexicon file is not valid JSON: {config['lexicon']}")
        lexicon = {}

    previous, run = None, 0
    for number, scene in enumerate(scenes, start=1):
        kind = scene["type"]
        run = run + 1 if kind == previous else 1
        previous = kind
        limit = MAX_TEXT_RUN if kind == "text" else MAX_RUN
        if run == limit + 1:
            add("warning", number, f"more than {limit} '{kind}' scenes in a row")

        if kind not in TYPES:
            add("error", number, f"unknown type '{kind}'")
        elif kind == "counter":
            if not re.fullmatch(r"[0-9]+", scene["value"]):
                add("error", number, f"@value must be English digits only, got '{scene['value']}'")
            if not scene["label"]:
                add("warning", number, "counter has no @label")
        elif kind == "bullets":
            items = [item.strip() for item in scene["items"].split("|") if item.strip()]
            if not items:
                add("error", number, "bullets scene has no @items")
            if len(items) > MAX_ITEMS:
                add("warning", number, f"{len(items)} items, keep it to {MAX_ITEMS}")
            for item in items:
                if len(item) > MAX_ITEM_CHARS:
                    add("warning", number, f"item is long ({len(item)} chars): {item[:20]}")

        text = spoken(scene)
        if re.search(r"à[¦§]", scene["text"]):
            add("error", number, "text looks garbled, save the script as UTF-8")
        word_count = len(text.split())
        if word_count > MAX_WORDS:
            add("warning", number, f"voiceover has {word_count} words, split the scene")

        if not scene["audio"]:
            prepared = prepare_speech(text, lexicon)
            if not re.search(r"\w", prepared):
                add("error", number, "nothing to speak in this scene")
            leftover = sorted(set(re.findall(r"[A-Za-z][A-Za-z0-9]*", prepared)))
            if leftover:
                add("warning", number, "add to lexicon.json: " + ", ".join(leftover))

        for key in ("audio", "image"):
            if scene[key] and not Path(scene[key]).exists():
                add("error", number, f"@{key} file not found: {scene[key]}")

    return issues