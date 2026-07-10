# TikTok Narrator

Paste text into a web page, pick an AI voice, and get back a vertical (9:16)
video with narration laid over looping gameplay footage — ready to upload.

## Setup

```bash
pip install -r requirements.txt
```

You also need `ffmpeg` installed and on your PATH:
- macOS: `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt install ffmpeg`
- Windows: download from ffmpeg.org and add it to PATH

## Add gameplay footage

Drop one or more `.mp4` (or `.mov`/`.mkv`/`.webm`) files into the `clips/`
folder. These are your background loops — think Minecraft parkour, Subway
Surfers-style runs, satisfying gameplay, etc.

**Use footage you have the rights to** — either record it yourself (a phone
or screen recording of you playing is the safest and most common approach
for this style of video) or footage explicitly licensed for reuse. Using
someone else's copyrighted gameplay recording can get a TikTok upload muted,
taken down, or struck.

Short clips are fine — the app automatically loops the clip to cover the
full length of the narration.

## Run it

```bash
python app.py
```

Then open http://localhost:5000 in your browser.

1. Paste your script into the text box.
2. Pick a narrator voice.
3. Optionally pick a specific background clip (or leave it random).
4. Click "Generate video". This can take anywhere from a few seconds to
   ~1 minute depending on script length and your machine.
5. Preview the result, then hit "Download video".

Finished videos land in `static/output/` as well, if you want to grab them
directly from disk.

## Notes / limits

- Narration is capped at 3 minutes; anything longer gets trimmed.
- Voices are generated with `edge-tts` (Microsoft's free neural TTS) — no
  API key needed, but it does require an internet connection.
- Output is always cropped/resized to 1080x1920 (standard TikTok vertical).
- Want burned-in captions? That's the natural next add-on — happy to build
  it if you want (e.g. using Whisper for auto-transcription + timed text
  overlays).

## Project structure

```
app.py                 Flask app + TTS + video composition
templates/index.html   Front-end UI
clips/                 Put your background gameplay clips here
static/output/         Generated videos land here
requirements.txt       Python dependencies
```
