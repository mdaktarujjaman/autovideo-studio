import hashlib
import json
import os
import shutil
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Manager
from pathlib import Path
from queue import Empty

from playwright.sync_api import sync_playwright

PALETTE = [
    ("#1e3a8a", "#0b1020"),
    ("#064e3b", "#07120e"),
    ("#4c1d95", "#0f0a1f"),
    ("#7f1d1d", "#140808"),
]

TEMPLATE = Path(__file__).parent / "templates" / "scene.html"
CACHE_ROOT = Path("build/cache")
IDLE_FPS = 8


def default_workers():
    return max(1, min(4, (os.cpu_count() or 2) // 2))


def background(scene, index):
    if scene["image"]:
        uri = Path(scene["image"]).resolve().as_uri()
        return f'url("{uri}") center / cover', True
    top, bottom = PALETTE[index % len(PALETTE)]
    return f"radial-gradient(circle at 50% 35%, {top}, {bottom})", False


def split_jobs(jobs, workers):
    groups = [[] for _ in range(workers)]
    loads = [0.0] * workers
    for job in sorted(jobs, key=lambda item: item["duration"], reverse=True):
        target = loads.index(min(loads))
        groups[target].append(job)
        loads[target] += job["duration"]
    return [group for group in groups if group]


def cache_key(data, size, fps, jpeg_quality, template, font_path):
    font = Path(font_path)
    font_stat = font.stat()
    fields = [
        data,
        list(size),
        fps,
        jpeg_quality,
        hashlib.sha1(template.encode("utf-8")).hexdigest(),
        str(font.resolve()),
        font_stat.st_size,
        int(font_stat.st_mtime),
    ]
    image = data.get("image")
    if image and Path(image).exists():
        image_stat = Path(image).stat()
        fields += [image_stat.st_size, int(image_stat.st_mtime)]
    raw = json.dumps(fields, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def _paths(key, names):
    folder = CACHE_ROOT / key
    return [str(folder / name) for name in names]


def _cached(key):
    listing = CACHE_ROOT / key / "paths.json"
    if not listing.exists():
        return None
    names = json.loads(listing.read_text(encoding="utf-8"))
    paths = _paths(key, names)
    if names and Path(paths[0]).exists() and Path(paths[-1]).exists():
        return paths
    return None


def _render_scene(page, template, font_uri, job, fps, step, jpeg_quality):
    folder = CACHE_ROOT / job["key"]
    shutil.rmtree(folder, ignore_errors=True)
    folder.mkdir(parents=True)

    data = json.dumps(job["data"], ensure_ascii=False).replace("</", "<\\/")
    html = template.replace("__FONT__", font_uri).replace("__SCENE__", data)
    page_file = folder / "scene.html"
    page_file.write_text(html, encoding="utf-8")
    page.goto(page_file.resolve().as_uri())
    page.evaluate("document.fonts.ready")

    active_ms = page.evaluate("window.activeUntil")
    total = max(1, int(job["duration"] * fps))
    full = min(total, int(active_ms * fps / 1000) + 1)

    names, last = [], None
    for n in range(total):
        if n < full or (n - full) % step == 0:
            page.evaluate(f"seek({n * 1000 / fps})")
            last = f"{n:05d}.jpg"
            page.screenshot(path=str(folder / last), type="jpeg", quality=jpeg_quality)
        names.append(last)

    (folder / "paths.json").write_text(json.dumps(names), encoding="utf-8")
    return names


class _Callback:
    def __init__(self, callback):
        self.callback = callback

    def put(self, _item):
        self.callback()


def _render_group(group, size, font_path, fps, jpeg_quality, report):
    template = TEMPLATE.read_text(encoding="utf-8")
    font_uri = Path(font_path).resolve().as_uri()
    step = max(1, round(fps / IDLE_FPS))
    results = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page(viewport={"width": size[0], "height": size[1]})
        for job in group:
            results[job["index"]] = _render_scene(
                page, template, font_uri, job, fps, step, jpeg_quality
            )
            report.put(job["index"])
        browser.close()

    return results


def render_scenes(
    scenes,
    durations,
    size,
    font_path,
    fps,
    progress=None,
    workers=None,
    jpeg_quality=92,
    use_cache=True,
    indexes=None,
):
    notify = progress or (lambda done, total: None)
    template = TEMPLATE.read_text(encoding="utf-8")
    indexes = indexes or list(range(len(scenes)))
    total = len(scenes)

    jobs = []
    for position, (scene, duration) in enumerate(zip(scenes, durations)):
        bg, dim = background(scene, indexes[position])
        data = {**scene, "bg": bg, "dim": dim, "duration": round(duration, 3)}
        key = cache_key(data, size, fps, jpeg_quality, template, font_path)
        jobs.append(
            {"index": position, "duration": duration, "data": data, "key": key}
        )

    sequences = {}
    pending = []
    for job in jobs:
        paths = _cached(job["key"]) if use_cache else None
        if paths is None:
            pending.append(job)
        else:
            sequences[job["index"]] = paths

    done = len(sequences)
    if done:
        notify(done, total)

    if pending:
        count = max(1, min(workers or default_workers(), len(pending)))
        groups = split_jobs(pending, count)

        if len(groups) == 1:
            def tick():
                nonlocal done
                done += 1
                notify(done, total)

            results = _render_group(
                groups[0], size, font_path, fps, jpeg_quality, _Callback(tick)
            )
            for index, names in results.items():
                sequences[index] = _paths(jobs[index]["key"], names)
        else:
            with Manager() as manager:
                events = manager.Queue()
                with ProcessPoolExecutor(max_workers=len(groups)) as pool:
                    futures = [
                        pool.submit(
                            _render_group,
                            group,
                            size,
                            font_path,
                            fps,
                            jpeg_quality,
                            events,
                        )
                        for group in groups
                    ]
                    while not all(future.done() for future in futures):
                        try:
                            events.get(timeout=0.5)
                        except Empty:
                            continue
                        done += 1
                        notify(done, total)
                    for future in futures:
                        for index, names in future.result().items():
                            sequences[index] = _paths(jobs[index]["key"], names)
                notify(total, total)

    return [sequences[position] for position in range(total)]