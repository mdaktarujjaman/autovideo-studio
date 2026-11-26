import numpy as np
from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    ImageSequenceClip,
    afx,
    concatenate_videoclips,
)

TRACK = 0.14
BAR_COLOR = (245, 197, 66)


def with_progress(frame, ratio):
    height, width = frame.shape[:2]
    thickness = max(4, round(min(width, height) * 0.01))
    out = frame.copy()
    strip = out[height - thickness:]
    strip[:] = (strip * (1 - TRACK) + 255 * TRACK).astype(np.uint8)
    strip[:, : int(width * min(max(ratio, 0.0), 1.0))] = BAR_COLOR
    return out


def build_video(sequences, voice_paths, output, fps, music="", crf=18, preset="medium"):
    clips = []
    for paths, voice_path in zip(sequences, voice_paths):
        audio = AudioFileClip(str(voice_path)).fx(afx.audio_normalize).volumex(0.85)
        clips.append(ImageSequenceClip(paths, fps=fps).set_audio(audio))

    video = concatenate_videoclips(clips, method="chain")
    length = video.duration
    video = video.fl(lambda get_frame, t: with_progress(get_frame(t), t / length))

    if music:
        background = (
            AudioFileClip(music)
            .fx(afx.audio_loop, duration=video.duration)
            .volumex(0.12)
        )
        video = video.set_audio(CompositeAudioClip([video.audio, background]))

    video.write_videofile(
        str(output),
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        audio_bitrate="192k",
        preset=preset,
        ffmpeg_params=["-crf", str(crf)],
    )
    return output