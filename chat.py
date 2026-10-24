"""Q-rious chat: the Gemini part of Aditya's qrious.py, as a web function.

Aditya's original is a desktop (tkinter) window, which a website can't use. This
file keeps the same idea and the same safety rules (answer only from the
supplied place data, never invent queue times) but has no window: the website's
chat panel calls ask() through the /api/ask route in api.py.

The Gemini key is read from the .env file (GEMINI_API_KEY=...). It is never
written in the code, so it never goes to GitHub.
"""

import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

# The first model is tried first. If Google says it doesn't exist for this key,
# the next one is tried. To force one, put GEMINI_MODEL=... in the .env file.
DEFAULT_MODELS = ["gemini-3.1-flash-lite-preview", "gemini-2.5-flash", "gemini-2.0-flash"]
TIMEOUT = (5, 25)  # seconds: connect, read
MAX_HISTORY = 8
MAX_TEXT = 500

SYSTEM_RULES = (
    "You are Q-rious, a friendly queue assistant for people in Oxford. "
    "Answer only questions about venues, queues, waiting times, walking times and "
    "opening hours. For unrelated questions, reply exactly: "
    "This is not my field of expertise. "
    "Use ONLY the supplied place data. Never invent venues, wait times, queue "
    "lengths, menus or opening hours. If the data does not say, say you don't know. "
    "If the user asks for a specific item (for example coconut milk), only recommend "
    "places whose 'sells' list includes it; never recommend a place that does not sell it. "
    "Among the places that qualify, compare total time = walk_minutes + wait_minutes and "
    "pick the lowest. Name your recommended place first in the reply, before mentioning "
    "any other place, and only mention others if it helps. Mention the walk time, the expected queue on arrival, and whether "
    "the queue is rising or dropping. Do not call figures real-time unless a place's "
    "source is 'live'. Keep answers to two or three short, friendly sentences, in "
    "British English."
)


def has_key():
    return bool((os.getenv("GEMINI_API_KEY") or "").strip())


def _models():
    first = (os.getenv("GEMINI_MODEL") or "").strip()
    return ([first] if first else []) + [m for m in DEFAULT_MODELS if m != first]


def _val(p, key, default="unknown"):
    v = p.get(key)
    return default if v is None or v == "" else v


def build_context(places):
    """Turn the list of places into plain text for Gemini."""
    lines = ["PLACE DATA (the only facts you may use):"]
    if not places:
        lines.append("No place data has been supplied. Do not invent venues.")
    for p in places:
        walk, wait = p.get("walk_minutes"), p.get("wait_minutes")
        total = walk + wait if isinstance(walk, (int, float)) and isinstance(wait, (int, float)) else "unknown"
        sells = ", ".join(p.get("sells") or []) or "unknown"
        lines.append(
            f"- id={_val(p, 'id')} | {_val(p, 'place')} ({_val(p, 'category')}): "
            f"walk {walk} min; queue now {_val(p, 'queue_now')} people; "
            f"expected queue on arrival {_val(p, 'queue_on_arrival')} people; "
            f"predicted wait {wait} min (range {_val(p, 'wait_low')} to {_val(p, 'wait_high')}); "
            f"trend {_val(p, 'trend')}; total time {total} min; sells: {sells}; "
            f"source: {_val(p, 'source')}."
        )
    return "\n".join(lines)


def _clean_history(history):
    out = []
    for m in (history or [])[-MAX_HISTORY:]:
        if not isinstance(m, dict):
            continue
        role = "Q-rious" if m.get("role") == "model" else "User"
        text = str(m.get("text", "")).strip()[:MAX_TEXT]
        if text:
            out.append(f"{role}: {text}")
    return out


def _call_gemini(prompt):
    """Returns (reply_text, error_code). error_code is None on success."""
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    if not key:
        return None, "no_key"

    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_RULES}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 300},
    }
    last_error = "network"

    for model in _models():
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        for attempt in range(2):
            try:
                r = requests.post(
                    url, json=payload, timeout=TIMEOUT,
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                )
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                last_error = "network"
                if attempt == 0:
                    time.sleep(1)
                    continue
                break  # try the next model

            if r.status_code in (429, 500, 502, 503, 504):
                last_error = "busy"
                if attempt == 0:
                    time.sleep(2)
                    continue
                break

            if r.status_code == 404:  # this model name isn't available: try the next
                last_error = "no_model"
                break

            if r.status_code in (401, 403) or (r.status_code == 400 and "API_KEY" in r.text):
                return None, "bad_key"

            if r.status_code != 200:
                last_error = "no_model" if "not found" in r.text.lower() else "empty"
                break

            try:
                parts = r.json()["candidates"][0]["content"]["parts"]
                reply = "".join(part.get("text", "") for part in parts).strip()
            except (KeyError, IndexError, ValueError, TypeError):
                reply = ""
            if reply:
                return reply, None
            last_error = "empty"
            break

    return None, last_error


def _find_place_id(reply, places):
    """The place whose name appears first in the reply (so the chat can offer a
    'Show on map' button)."""
    low = reply.lower()
    best_id, best_pos = None, None
    for p in places:
        name = str(p.get("place", "")).lower()
        pos = low.find(name) if name else -1
        if pos >= 0 and (best_pos is None or pos < best_pos):
            best_id, best_pos = p.get("id"), pos
    return best_id


def ask(message, history, places):
    """The one function the website calls.

    message : what the user just typed
    history : earlier turns, a list like [{"role": "user" or "model", "text": "..."}]
    places  : the list from places_data.get_places()

    Returns {"reply": text, "place_id": id or None, "error": code or None}.
    """
    prompt = "\n\n".join([
        build_context(places),
        "CONVERSATION SO FAR:\n" + ("\n".join(_clean_history(history)) or "(none)"),
        f"LATEST USER MESSAGE: {str(message).strip()[:MAX_TEXT]}",
        "Answer the latest message using only the place data above.",
    ])
    reply, error = _call_gemini(prompt)
    if error:
        return {"reply": "", "place_id": None, "error": error}
    return {"reply": reply, "place_id": _find_place_id(reply, places), "error": None}
