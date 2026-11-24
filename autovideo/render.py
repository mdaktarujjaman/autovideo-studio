import json
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

PALETTE = [
    ("#1e3a8a", "#0b1020"),
    ("#064e3b", "#07120e"),
    ("#4c1d95", "#0f0a1f"),
    ("#7f1d1d", "#140808"),
]

TEMPLATE = Path(__file__).parent / "templates" / "scene.html"
ANIM_SECONDS = 5.0


def background(scene, index):
    if scene["image"]:
        uri = Path(scene["image"]).resolve().as_uri()
        return f'url("{uri}") center / cover', True
    top, bottom = PALETTE[index % len(PALETTE)]
    return f"radial-gradient(circle at 50% 35%, {top}, {bottom})", False


def render_scenes(scenes, durations, size, font_path, fps, progress=None):
    width, height = size
    template = TEMPLATE.read_text(encoding="utf-8")
    font_uri = Path(font_path).resolve().as_uri()
    root = Path("build")
    frames_root = root / "frames"
    shutil.rmtree(frames_root, ignore_errors=True)
    sequences = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})

        for index, (scene, duration) in enumerate(zip(scenes, durations)):
            bg, dim = background(scene, index)
            data = json.dumps({**scene, "bg": bg, "dim": dim}, ensure_ascii=False)
            html = template.replace("__FONT__", font_uri).replace(
                "__SCENE__", data.replace("</", "<\\/")
            )
            page_file = root / f"scene_{index}.html"
            page_file.write_text(html, encoding="utf-8")
            page.goto(page_file.resolve().as_uri())
            page.evaluate("document.fonts.ready")

            total = max(1, int(duration * fps))
            animated = min(total, int(ANIM_SECONDS * fps))
            folder = frames_root / f"scene_{index}"
            folder.mkdir(parents=True, exist_ok=True)

            paths = []
            for n in range(animated):
                page.evaluate(f"seek({n * 1000 / fps})")
                path = folder / f"{n:05d}.jpg"
                page.screenshot(path=str(path), type="jpeg", quality=92)
                paths.append(str(path))

            paths += [paths[-1]] * (total - animated)
            sequences.append(paths)
            if progress:
                progress(index + 1, len(scenes))

        browser.close()

    return sequences