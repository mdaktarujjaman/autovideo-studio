import argparse
from pathlib import Path

from .lexicon import load_lexicon
from .parser import parse
from .pipeline import SIZES, render_script
from .speech import prepare_speech
from .validator import estimate_seconds, validate


def _progress(stage, done, total):
    print(f"{stage}: {done}/{total}", flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="autovideo", description="Turn a script file into an animated MP4"
    )
    parser.add_argument("script", help="path to the script file")
    parser.add_argument("-f", "--format", choices=[*SIZES, "both"], default="portrait")
    parser.add_argument("-o", "--output-dir", default="output")
    parser.add_argument("--check", action="store_true", help="validate the script and exit")
    parser.add_argument("--speak", action="store_true", help="print the spoken text and exit")
    args = parser.parse_args(argv)

    if not Path(args.script).exists():
        print(f"script not found: {args.script}")
        return 1

    config, scenes = parse(args.script)
    issues = validate(config, scenes)
    for issue in issues:
        print(issue)
    minutes = estimate_seconds(scenes) / 60
    print(f"{len(scenes)} scenes, estimated length {minutes:.1f} min")

    if any(issue.level == "error" for issue in issues):
        return 1

    if args.speak:
        lexicon = load_lexicon(config["lexicon"])
        for number, scene in enumerate(scenes, start=1):
            if scene["audio"]:
                print(f"{number}. [recorded audio] {scene['audio']}")
            else:
                print(f"{number}. {prepare_speech(scene['say'] or scene['text'], lexicon)}")
        return 0

    if args.check:
        return 0

    results = render_script(args.script, args.format, args.output_dir, _progress)
    for name, path in results.items():
        print(f"saved ({name}): {path}")
    return 0