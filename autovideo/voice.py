import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
import wave
from pathlib import Path

import edge_tts
import imageio_ffmpeg

PAUSE = 0.28
GEMINI_GAP = 6.5
CACHE_VERSION = 3

TRIM = (
    "silenceremove=start_periods=1:start_silence=0.2:start_threshold=-50dB,"
    "areverse,"
    "silenceremove=start_periods=1:start_silence=0.12:start_threshold=-50dB,"
    "areverse"
)


async def _save(text, voice, rate, pitch, path):
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(str(path))


def _sentences(text):
    parts = re.split(r"(?<=[।?!])\s+", text.strip())
    return [part for part in parts if part]


def _ffmpeg(args):
    subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", *args],
        check=True,
        capture_output=True,
    )


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
    _ffmpeg([*inputs, "-filter_complex", graph, "-map", "[out]", str(output)])


def _trim(path):
    temp = path.with_name(f"{path.stem}_trim{path.suffix}")
    _ffmpeg(["-i", str(path), "-af", TRIM, str(temp)])
    temp.replace(path)


def _edge(text, config, path):
    sentences = _sentences(text)
    parts = [path.with_name(f"{path.stem}_part{i}.mp3") for i in range(len(sentences))]

    async def run():
        await asyncio.gather(
            *(
                _save(s, config["voice"], config["rate"], config["pitch"], p)
                for s, p in zip(sentences, parts)
            )
        )

    asyncio.run(run())
    _join(parts, path)
    for part in parts:
        part.unlink(missing_ok=True)


def _gemini(text, config, path):
    from google import genai
    from google.genai import types

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise SystemExit("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=key)
    prompt = f"{config['style']}: {text}"
    settings = types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=config["gemini_voice"]
                )
            )
        ),
    )

    pcm = None
    for attempt in range(5):
        try:
            response = client.models.generate_content(
                model=config["tts_model"], contents=prompt, config=settings
            )
            pcm = response.candidates[0].content.parts[0].inline_data.data
            break
        except Exception as error:
            print(f"gemini retry {attempt + 1}: {error}")
            if attempt == 4:
                raise
            time.sleep(15 * (attempt + 1))

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(pcm)

    time.sleep(GEMINI_GAP)


def synthesize(text, config, folder="build/voice_cache"):
    provider = config["provider"]
    fields = [CACHE_VERSION, provider, text]
    if provider == "gemini":
        fields += [config["gemini_voice"], config["style"], config["tts_model"]]
    else:
        fields += [config["voice"], config["rate"], config["pitch"]]

    key = hashlib.sha1(json.dumps(fields, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    path = Path(folder) / f"{key}.{'wav' if provider == 'gemini' else 'mp3'}"
    if path.exists():
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    if provider == "gemini":
        _gemini(text, config, path)
    else:
        _edge(text, config, path)
    _trim(path)
    return path