import sys
import argparse
import time
from pathlib import Path

from .lexicon import load_lexicon
from .parser import parse
from .pipeline import SIZES, parse_selection, render_script
from .render import default_workers
from .speech import prepare_speech
from .validator import estimate_seconds, validate


_started = time.time()


def _progress(stage, done, total):
    print(f"{stage}: {done}/{total}  ({time.time() - _started:.0f}s)", flush=True)


def main(argv=None):
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        prog="autovideo", description="Turn a script file into an animated MP4"
    )
    parser.add_argument("script", help="path to the script file")
    parser.add_argument("-f", "--format", choices=[*SIZES, "both"], default="portrait")
    parser.add_argument("-o", "--output-dir", default="output")
    parser.add_argument("--scenes", default="", help="scene numbers to render, e.g. 5-8 or 1,3-4")
    parser.add_argument("--draft", action="store_true", help="fast low-quality preview")
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help=f"parallel browsers (default {default_workers()})",
    )
    parser.add_argument("--no-cache", action="store_true", help="re-render every scene")
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

    try:
        numbers = parse_selection(args.scenes, len(scenes))
    except ValueError as error:
        print(error)
        return 1

    if args.speak:
        lexicon = load_lexicon(config["lexicon"])
        for number in numbers:
            scene = scenes[number - 1]
            if scene["audio"]:
                print(f"{number}. [recorded audio] {scene['audio']}")
            else:
                print(f"{number}. {prepare_speech(scene['say'] or scene['text'], lexicon)}")
        return 0

    if args.check:
        return 0

    started = time.time()
    try:
        results = render_script(
            args.script,
            args.format,
            args.output_dir,
            _progress,
            scenes_spec=args.scenes,
            draft=args.draft,
            workers=args.workers,
            use_cache=not args.no_cache,
        )
    except RuntimeError as error:
        print(error)
        return 1

    print(f"render time: {(time.time() - started) / 60:.1f} min")
    for name, path in results.items():
        print(f"saved ({name}): {path}")
    return 0