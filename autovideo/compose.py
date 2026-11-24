from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    ImageSequenceClip,
    afx,
    concatenate_videoclips,
)


def build_video(sequences, voice_paths, output, fps, music=""):
    clips = []
    for paths, voice_path in zip(sequences, voice_paths):
        audio = AudioFileClip(str(voice_path))
        clips.append(ImageSequenceClip(paths, fps=fps).set_audio(audio))

    video = concatenate_videoclips(clips, method="chain")

    if music:
        background = (
            AudioFileClip(music)
            .fx(afx.audio_loop, duration=video.duration)
            .volumex(0.12)
        )
        video = video.set_audio(CompositeAudioClip([video.audio, background]))

    video.write_videofile(str(output), fps=fps, codec="libx264", audio_codec="aac")
    return output