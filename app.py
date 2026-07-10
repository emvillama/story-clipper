import asyncio
import os
import random
import uuid
import yt_dlp

import edge_tts
from flask import Flask, render_template, request, jsonify, send_from_directory
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIPS_DIR = os.path.join(BASE_DIR, "clips")
OUTPUT_DIR = os.path.join(BASE_DIR, "static", "output")
MAX_DURATION_SECONDS = 180  # 3 minute cap

os.makedirs(CLIPS_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = Flask(__name__)

# A small curated set of good narrator voices. Full list: `edge-tts --list-voices`
VOICES = {
    "Guy (US, male)": "en-US-GuyNeural",
    "Aria (US, female)": "en-US-AriaNeural",
    "Jenny (US, female)": "en-US-JennyNeural",
    "Eric (US, male, deep)": "en-US-EricNeural",
    "Ryan (UK, male)": "en-GB-RyanNeural",
    "Sonia (UK, female)": "en-GB-SoniaNeural",
}


def list_clips():
    valid_ext = (".mp4", ".mov", ".mkv", ".webm")
    if not os.path.isdir(CLIPS_DIR):
        return []
    return sorted(f for f in os.listdir(CLIPS_DIR) if f.lower().endswith(valid_ext))

def download_youtube_video(url):
    opts = {
        "format": "bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(CLIPS_DIR, "%(title)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    # yt-dlp may have merged into mp4
    base = os.path.splitext(filename)[0]
    mp4 = base + ".mp4"

    if os.path.exists(mp4):
        return os.path.basename(mp4)

    return os.path.basename(filename)

async def synthesize_speech(text: str, voice: str, out_path: str):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(out_path)


def make_vertical(clip, target_w=1080, target_h=1920):
    """Center-crop then resize a clip to fill a 9:16 vertical frame."""
    target_ratio = target_w / target_h
    w, h = clip.w, clip.h
    current_ratio = w / h

    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        x1 = (w - new_w) // 2
        clip = clip.cropped(x1=x1, y1=0, x2=x1 + new_w, y2=h)
    else:
        new_h = int(w / target_ratio)
        y1 = (h - new_h) // 2
        clip = clip.cropped(x1=0, y1=y1, x2=w, y2=y1 + new_h)

    return clip.resized((target_w, target_h))


def build_background(duration: float, chosen_clip: str | None):
    clip_name = chosen_clip or random.choice(list_clips())
    clip_path = os.path.join(CLIPS_DIR, clip_name)
    source = VideoFileClip(clip_path)

    # Loop the source clip until it's at least as long as the narration
    segments = []
    covered = 0.0
    while covered < duration:
        segments.append(source)
        covered += source.duration

    video = concatenate_videoclips(segments) if len(segments) > 1 else source
    video = video.subclipped(0, duration)
    video = make_vertical(video)
    video = video.without_audio()
    return video, clip_name


@app.route("/")
def index():
    return render_template("index.html", voices=VOICES, clips=list_clips())


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    text = (data.get("text") or "").strip()
    voice_key = data.get("voice") or next(iter(VOICES))
    chosen_clip = data.get("clip") or None

    if not text:
        return jsonify({"error": "No text provided."}), 400
    if not list_clips():
        return jsonify({"error": "No gameplay clips found in the clips/ folder. Add an .mp4 file there first."}), 400

    voice = VOICES.get(voice_key, voice_key)
    job_id = uuid.uuid4().hex[:10]
    audio_path = os.path.join(OUTPUT_DIR, f"{job_id}_narration.mp3")
    video_path = os.path.join(OUTPUT_DIR, f"{job_id}_final.mp4")

    try:
        asyncio.run(synthesize_speech(text, voice, audio_path))

        narration = AudioFileClip(audio_path)
        duration = min(narration.duration, MAX_DURATION_SECONDS)
        narration = narration.subclipped(0, duration)

        background, used_clip = build_background(duration, chosen_clip)
        final = background.with_audio(narration)

        final.write_videofile(
            video_path,
            fps=30,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            threads=4,
            logger=None,
        )

        narration.close()
        background.close()
        final.close()

        truncated = narration.duration >= MAX_DURATION_SECONDS
        return jsonify({
            "video_url": f"/static/output/{job_id}_final.mp4",
            "clip_used": used_clip,
            "duration": round(duration, 1),
            "truncated": truncated,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download_clip", methods=["POST"])
def download_clip():

    data = request.get_json()

    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "No YouTube URL supplied"}), 400

    try:
        filename = download_youtube_video(url)

        return jsonify({
            "success": True,
            "filename": filename,
            "clips": list_clips()
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)