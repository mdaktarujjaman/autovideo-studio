import asyncio
import re
import shutil
import subprocess
from pathlib import Path

import edge_tts
import imageio_ffmpeg

PAUSE = 0.28


async def _save(text, voice, rate, pitch, path):
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(str(path))


def _sentences(text):
    parts = re.split(r"(?<=[।?!])\s+", text.strip())
    return [part for part in parts if part]


def _join(parts, output):
    if len(parts) == 1:
        shutil.copy(parts[0], output)
        return

    inputs, chains, labels = [], [], []
    for i, part in enumerate(parts):
        inputs += ["-i", str(part)]
        pad = f",apad=pad_dur={PAUSE}" if i < len(parts) - 1 else ""
        chains.append(f"[{i}:a]aresample=24000{pad}[a{i}]")
        labels.append(f"[a{i}]")

    graph = ";".join(chains) + ";" + "".join(labels)
    graph += f"concat=n={len(parts)}:v=0:a=1[out]"

    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", *inputs,
         "-filter_complex", graph, "-map", "[out]", str(output)],
        check=True,
        capture_output=True,
    )


def synthesize(text, voice, path, rate="-5%", pitch="+0Hz"):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sentences = _sentences(text)
    parts = [path.with_name(f"{path.stem}_part{i}.mp3") for i in range(len(sentences))]

    async def run():
        await asyncio.gather(
            *(_save(s, voice, rate, pitch, p) for s, p in zip(sentences, parts))
        )

    asyncio.run(run())
    _join(parts, path)
    return path