import sys
from pathlib import Path

from moviepy.editor import AudioFileClip

from autovideo.compose import build_video
from autovideo.parser import parse
from autovideo.render import render_scenes
from autovideo.voice import synthesize

PAD = 0.6
SIZES = {"portrait": (1080, 1920), "landscape": (1920, 1080)}


def main(script_path, mode):
    config, scenes = parse(script_path)

    build = Path("build")
    output_dir = Path("output")
    build.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)

    voices = [
        synthesize(
            scene["say"] or scene["text"],
            config["voice"],
            build / f"voice_{i}.mp3",
            config["rate"],
            config["pitch"],
        )
        for i, scene in enumerate(scenes)
    ]

    durations = []
    for voice in voices:
        audio = AudioFileClip(str(voice))
        durations.append(audio.duration + PAD)
        audio.close()

    names = list(SIZES) if mode == "both" else [mode]
    for name in names:
        sequences = render_scenes(
            scenes, durations, SIZES[name], config["font"], config["fps"]
        )
        output = output_dir / f"{Path(script_path).stem}_{name}.mp4"
        build_video(sequences, voices, output, config["fps"], config["music"])
        print(f"saved: {output}")


if __name__ == "__main__":
    script = sys.argv[1] if len(sys.argv) > 1 else "scripts/demo.txt"
    chosen = sys.argv[2] if len(sys.argv) > 2 else "portrait"
    if chosen not in ("portrait", "landscape", "both"):
        sys.exit("mode must be portrait, landscape or both")
    main(script, chosen)