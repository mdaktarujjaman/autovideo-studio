from pathlib import Path

from moviepy.editor import AudioFileClip

from .compose import build_video
from .lexicon import load_lexicon
from .parser import parse
from .render import render_scenes
from .speech import prepare_speech
from .validator import validate
from .voice import synthesize

PAD = 0.6
SIZES = {"portrait": (1080, 1920), "landscape": (1920, 1080)}


class ScriptError(Exception):
    def __init__(self, issues):
        self.issues = issues
        super().__init__("\n".join(str(issue) for issue in issues))


def voice_for(scene, config, lexicon):
    if scene["audio"]:
        return Path(scene["audio"])
    text = prepare_speech(scene["say"] or scene["text"], lexicon)
    return synthesize(text, config)


def render_script(script_path, mode="portrait", output_dir="output", progress=None):
    if mode != "both" and mode not in SIZES:
        raise ValueError(f"unknown format '{mode}'")

    notify = progress or (lambda stage, done, total: None)
    config, scenes = parse(script_path)

    issues = validate(config, scenes)
    if any(issue.level == "error" for issue in issues):
        raise ScriptError(issues)

    lexicon = load_lexicon(config["lexicon"])

    Path("build").mkdir(exist_ok=True)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    voices = []
    for index, scene in enumerate(scenes):
        voices.append(voice_for(scene, config, lexicon))
        notify("voice", index + 1, len(scenes))

    durations = []
    for voice in voices:
        audio = AudioFileClip(str(voice))
        durations.append(audio.duration + PAD)
        audio.close()

    names = list(SIZES) if mode == "both" else [mode]
    results = {}
    for name in names:
        sequences = render_scenes(
            scenes,
            durations,
            SIZES[name],
            config["font"],
            config["fps"],
            progress=lambda done, total, n=name: notify(f"render-{n}", done, total),
        )
        target = target_dir / f"{Path(script_path).stem}_{name}.mp4"
        notify(f"encode-{name}", 0, 1)
        build_video(sequences, voices, target, config["fps"], config["music"])
        notify(f"encode-{name}", 1, 1)
        results[name] = target

    return results