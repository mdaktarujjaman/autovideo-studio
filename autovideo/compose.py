import subprocess
from pathlib import Path

import imageio_ffmpeg
from moviepy.editor import AudioFileClip, CompositeAudioClip, afx

BAR_COLOR = "0xF5C542"
TRACK_ALPHA = 0.14


def collapse_runs(sequences):
    runs = []
    for paths in sequences:
        for path in paths:
            if runs and runs[-1][0] == path:
                runs[-1][1] += 1
            else:
                runs.append([path, 1])
    return runs


def write_concat(runs, fps, target):
    def entry(path):
        safe = Path(path).resolve().as_posix().replace("'", "'\\''")
        return f"file '{safe}'"

    rows = []
    for path, count in runs:
        rows.append(entry(path))
        rows.append(f"duration {count / fps:.6f}")
    rows.append(entry(runs[-1][0]))
    Path(target).write_text("\n".join(rows) + "\n", encoding="utf-8")


def build_audio(voice_paths, lengths, music, target):
    clips, start = [], 0.0
    for voice_path, length in zip(voice_paths, lengths):
        clip = AudioFileClip(str(voice_path)).fx(afx.audio_normalize).volumex(0.85)
        clips.append(clip.set_start(start))
        start += length

    if music:
        background = (
            AudioFileClip(music).fx(afx.audio_loop, duration=start).volumex(0.12)
        )
        clips.append(background.set_start(0))

    mix = CompositeAudioClip(clips).set_duration(start)
    mix.write_audiofile(
        str(target),
        fps=44100,
        codec="aac",
        bitrate="192k",
        ffmpeg_params=["-ac", "2"],
        logger=None,
    )
    for clip in clips:
        clip.close()


def build_video(
    sequences,
    voice_paths,
    output,
    fps,
    size,
    music="",
    crf=18,
    preset="medium",
    progress=None,
):
    output = Path(output)
    work = Path("build")
    work.mkdir(exist_ok=True)

    total_frames = sum(len(paths) for paths in sequences)
    duration = total_frames / fps
    lengths = [len(paths) / fps for paths in sequences]

    audio = work / f"{output.stem}.m4a"
    build_audio(voice_paths, lengths, music, audio)

    listing = work / f"{output.stem}_frames.txt"
    write_concat(collapse_runs(sequences), fps, listing)

    width, height = size
    thickness = max(4, round(min(width, height) * 0.01))
    graph = (
        f"[0:v]fps={fps},scale=in_range=pc:out_range=tv,format=yuv420p,"
        f"drawbox=x=0:y=ih-{thickness}:w=iw:h={thickness}:"
        f"color=white@{TRACK_ALPHA}:t=fill[base];"
        f"[base][1:v]overlay=x=-w+w*t/{duration:.3f}:y=H-h:shortest=1[v]"
    )

    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-y",
        "-loglevel", "error",
        "-progress", "pipe:1",
        "-nostats",
        "-f", "concat",
        "-safe", "0",
        "-i", str(listing),
        "-f", "lavfi",
        "-i", f"color=c={BAR_COLOR}:s={width}x{thickness}:r={fps},format=yuv420p",
        "-i", str(audio),
        "-filter_complex", graph,
        "-map", "[v]",
        "-map", "2:a",
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        "-t", f"{duration:.3f}",
        str(output),
    ]

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    step = max(1, total_frames // 20)
    reported = 0
    for line in process.stdout:
        if line.startswith("frame="):
            done = int(line.split("=")[1])
            if progress and done // step > reported:
                reported = done // step
                progress(min(done, total_frames), total_frames)

    errors = process.stderr.read()
    if process.wait() != 0:
        raise RuntimeError(f"ffmpeg failed: {errors.strip()[-600:]}")
    if progress:
        progress(total_frames, total_frames)
    return output