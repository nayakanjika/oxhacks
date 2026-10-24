"""Q-rious voice: ElevenLabs speaking and listening, kept on the server.

    GET  /api/voice-status   {enabled: true/false}  (is ELEVENLABS_API_KEY in .env?)
    POST /api/speak          {text}   -> an mp3 of the text read aloud
    POST /api/transcribe     audio file -> {text}

The key stays in the .env file and never reaches the browser. If anything goes
wrong, the website falls back to the browser's built-in voice, so the demo
never goes silent.
"""

import os

import requests
from dotenv import load_dotenv
from flask import Blueprint, Response, jsonify, request

load_dotenv()

voice = Blueprint("voice", __name__, url_prefix="/api")

API = "https://api.elevenlabs.io/v1"
DEFAULT_VOICE = "JBFqnCBsd6RMkjVDRZzb"  # change with ELEVENLABS_VOICE_ID in .env
TIMEOUT = (5, 25)


def _key():
    return (os.getenv("ELEVENLABS_API_KEY") or "").strip()


@voice.get("/voice-status")
def status():
    return jsonify(enabled=bool(_key()))


@voice.post("/speak")
def speak():
    if not _key():
        return jsonify(error="no_key"), 503
    data = request.get_json(silent=True) or {}
    text = str(data.get("text", "")).strip()[:600]
    if not text:
        return jsonify(error="empty"), 400
    voice_id = (os.getenv("ELEVENLABS_VOICE_ID") or DEFAULT_VOICE).strip()
    try:
        r = requests.post(
            f"{API}/text-to-speech/{voice_id}?output_format=mp3_44100_64",
            headers={"xi-api-key": _key(), "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_flash_v2_5"},
            timeout=TIMEOUT)
    except requests.exceptions.RequestException:
        return jsonify(error="network"), 502
    if r.status_code != 200:
        return jsonify(error="elevenlabs_%s" % r.status_code), 502
    return Response(r.content, mimetype="audio/mpeg")


@voice.post("/transcribe")
def transcribe():
    if not _key():
        return jsonify(error="no_key"), 503
    audio = request.files.get("audio")
    if not audio:
        return jsonify(error="no_audio"), 400
    blob = audio.read()
    if not blob or len(blob) > 5_000_000:
        return jsonify(error="bad_audio"), 400
    try:
        r = requests.post(
            f"{API}/speech-to-text",
            headers={"xi-api-key": _key()},
            data={"model_id": "scribe_v1", "language_code": "eng"},
            files={"file": (audio.filename or "speech.webm", blob, audio.mimetype or "audio/webm")},
            timeout=(5, 40))
    except requests.exceptions.RequestException:
        return jsonify(error="network"), 502
    if r.status_code != 200:
        return jsonify(error="elevenlabs_%s" % r.status_code), 502
    try:
        text = str(r.json().get("text", "")).strip()
    except ValueError:
        text = ""
    return jsonify(text=text)
