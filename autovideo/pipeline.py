import re
from pathlib import Path

from moviepy.editor import AudioFileClip

from .compose import build_video
from .lexicon import load_lexicon
from .parser import parse
from .render import render_scenes
from .speech import prepare_speech
from .validator import validate
from .voice import synthesize

PAD = 0.3
SIZES = {"portrait": (1080, 1920), "landscape": (1920, 1080)}
DRAFT = {"scale": 0.5, "fps": 12, "jpeg": 70, "crf": 28, "preset": "ultrafast"}
FINAL = {"scale": 1.0, "fps": None, "jpeg": 92, "crf": 18, "preset": "medium"}


class ScriptError(Exception):
    def __init__(self, issues):
        self.issues = issues
        super().__init__("\n".join(str(issue) for issue in issues))


def parse_selection(text, count):
    if not text or not text.strip():
        return list(range(1, count + 1))

    chosen = set()
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        match = re.fullmatch(r"(\d+)(?:-(\d+))?", part)
        if not match:
            raise ValueError(f"bad scene selection '{part}'")
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if start < 1 or end > count or start > end:
            raise ValueError(f"scene selection '{part}' is outside 1-{count}")
        chosen.update(range(start, end + 1))
    return sorted(chosen)


def scaled(size, scale):
    return tuple(max(2, int(value * scale) // 2 * 2) for value in size)


def voice_for(scene, config, lexicon):
    if scene["audio"]:
        return Path(scene["audio"])
    text = prepare_speech(scene["say"] or scene["text"], lexicon)
    return synthesize(text, config)


def render_script(
    script_path,
    mode="portrait",
    output_dir="output",
    progress=None,
    scenes_spec="",
    draft=False,
    workers=None,
    use_cache=True,
):
    if mode != "both" and mode not in SIZES:
        raise ValueError(f"unknown format '{mode}'")

    notify = progress or (lambda stage, done, total: None)
    config, all_scenes = parse(script_path)

    issues = validate(config, all_scenes)
    if any(issue.level == "error" for issue in issues):
        raise ScriptError(issues)

    numbers = parse_selection(scenes_spec, len(all_scenes))
    scenes = [all_scenes[number - 1] for number in numbers]
    indexes = [number - 1 for number in numbers]

    lexicon = load_lexicon(config["lexicon"])
    quality = DRAFT if draft else FINAL
    fps = quality["fps"] or config["fps"]

    Path("build").mkdir(exist_ok=True)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    voices = []
    for position, scene in enumerate(scenes):
        try:
            voices.append(voice_for(scene, config, lexicon))
        except Exception as error:
            number = indexes[position] + 1
            spoken = prepare_speech(scene["say"] or scene["text"], lexicon)
            raise RuntimeError(
                f"voice failed for scene {number}: {spoken[:70]!r} ({error})"
            ) from error
        notify("voice", position + 1, len(scenes))

    durations = []
    for voice in voices:
        audio = AudioFileClip(str(voice))
        durations.append(audio.duration + PAD)
        audio.close()

    suffix = ""
    if scenes_spec.strip():
        suffix += "_s" + scenes_spec.replace(",", "+").replace(" ", "")
    if draft:
        suffix += "_draft"

    names = list(SIZES) if mode == "both" else [mode]
    results = {}
    for name in names:
        sequences = render_scenes(
            scenes,
            durations,
            scaled(SIZES[name], quality["scale"]),
            config["font"],
            fps,
            progress=lambda done, total, n=name: notify(f"render-{n}", done, total),
            workers=workers,
            jpeg_quality=quality["jpeg"],
            use_cache=use_cache,
            indexes=indexes,
        )
        target = target_dir / f"{Path(script_path).stem}{suffix}_{name}.mp4"
        notify(f"encode-{name}", 0, 1)
        build_video(
            sequences,
            voices,
            target,
            fps,
            config["music"],
            crf=quality["crf"],
            preset=quality["preset"],
        )
        notify(f"encode-{name}", 1, 1)
        results[name] = target

    return results