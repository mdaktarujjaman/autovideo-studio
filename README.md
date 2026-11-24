# autovideo-studio

Turn a plain text script into a ready-to-publish animated MP4. Write the script once, run one command, and get a narrated video in portrait (Reels/Shorts) and landscape (YouTube) formats.

## Features

- One command from script to MP4: `python run.py scripts/my_video.txt both`
- Portrait (1080x1920) and landscape (1920x1080) from the same script
- Animated scene types: headline text, counting numbers with icons, sliding bullet lists
- Bangla text rendered correctly through Chromium (proper conjuncts and vowel signs)
- Voiceover providers: Edge TTS, Gemini TTS, or your own recorded audio per scene
- Voice caching, so re-rendering does not regenerate or re-spend quota
- Scene length follows the voiceover length automatically

## How it works

```
script.txt -> parser -> voiceover per scene -> HTML scene template
-> Chromium (Playwright) captures frames -> MoviePy composes -> MP4
```

## Project structure

```
autovideo-studio/
├── autovideo/
│   ├── parser.py        script file -> config and scenes
│   ├── voice.py         voice providers and caching
│   ├── render.py        scene frames via Playwright
│   ├── compose.py       frames and audio -> MP4
│   └── templates/
│       └── scene.html   animated scene template
├── assets/
│   ├── fonts/           put NotoSansBengali.ttf here
│   ├── music/
│   └── images/
├── scripts/             your script files
├── build/               temporary files (ignored by git)
├── output/              finished videos (ignored by git)
└── run.py               entry point
```

## Setup

Requires Python 3.10 or newer.

```bash
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux / macOS
pip install -r requirements.txt
playwright install chromium
```

Download Noto Sans Bengali from Google Fonts and save it as `assets/fonts/NotoSansBengali.ttf`.

## Usage

```bash
python run.py scripts/demo.txt portrait
python run.py scripts/demo.txt landscape
python run.py scripts/demo.txt both
```

Output files are written to `output/` as `<script name>_portrait.mp4` and `<script name>_landscape.mp4`.

## Script format

Scenes are separated by one blank line. Lines starting with `@` are settings; the other lines are the scene text, which is also the voiceover unless `@say` is set.

Global settings (anywhere in the file):

| Setting | Meaning | Default |
|---|---|---|
| `@provider` | `edge` or `gemini` | `edge` |
| `@voice` | Edge TTS voice name | `bn-BD-NabanitaNeural` |
| `@rate`, `@pitch` | Edge TTS speed and pitch | `-5%`, `+0Hz` |
| `@gemini_voice` | Gemini voice name | `Sulafat` |
| `@style` | Gemini speaking style prompt | natural, warm Bangla |
| `@music` | Background music file | none |
| `@fps` | Frames per second | `24` |

Scene settings:

| Setting | Meaning |
|---|---|
| `@type` | `text` (default), `counter`, or `bullets` |
| `@value` | Number for `counter` (digits only) |
| `@label` | Text beside the counter number |
| `@icon` | `person`, `dot`, or `none` for counter icons |
| `@items` | Bullet items separated by `\|` (up to 3 recommended) |
| `@say` | Voiceover text that differs from the on-screen text |
| `@audio` | Path to your own recorded audio for this scene |
| `@image` | Background image for the scene |

Example:

```
@voice bn-BD-NabanitaNeural
@rate -5%

@say শপভার্জ দিয়ে আপনার স্টোর হবে আরও স্মার্ট।
ShopVerge দিয়ে আপনার স্টোর হবে আরও স্মার্ট

@type counter
@value 24
@label ঘণ্টা সাপোর্ট
@icon none
প্রতিদিন চব্বিশ ঘণ্টা গ্রাহকের প্রশ্নের উত্তর দেয়।

@type bullets
@items দ্রুত সেটআপ|নিজের API key|WooCommerce রেডি
মাত্র কয়েক মিনিটে ইনস্টল করে লাইভ হয়ে যান।
```

## Voice providers

**Edge TTS** works out of the box and needs an internet connection.

**Gemini TTS** needs an API key in an environment variable. Never commit the key.

```powershell
$env:GEMINI_API_KEY="your_key"
```

Then add `@provider gemini` to the script. Free tier limits apply.

**Your own voice**: record one file per scene and point to it with `@audio assets/voice/scene01.wav`.

## Notes and limitations

- Scene animations play during the first few seconds, then the frame holds while the narration continues
- Rendering an 8-minute video takes a while because every animated frame is captured from Chromium
- Temporary frames are stored in `build/frames`; keep a few GB of free disk space

## Roadmap

- Idle motion so long scenes never freeze
- More scene types: news card, quote, scoreboard, timeline, progress ring
- Automatic scene type selection
- Scene transitions
- GitHub Actions workflow to render videos from a button
- Voice cloning provider