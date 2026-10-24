"""Q-rious: the routes the app screen talks to (all under /api).

    GET  /api/health   quick check: is the server up, is the Gemini key loaded?
    GET  /api/places   the places and queue numbers (from places_data.py)
    POST /api/ask      the chat: {message, history} -> {reply, place_id, error}
    POST /api/report   "Report a queue": {place_id, level} -> {ok}

app.py registers this file with two lines. Teammates: change places_data.py
(Tiger Data) and chat.py (Gemini), not this file.
"""

from flask import Blueprint, jsonify, request, session

import chat
import places_data

api = Blueprint("api", __name__, url_prefix="/api")


@api.get("/health")
def health():
    # Never returns the key itself, only whether it was found.
    found = places_data.get_places()
    return jsonify(ok=True, gemini_key_loaded=chat.has_key(),
                   places=len(found),
                   tiger_data_configured=places_data.db_configured(),
                   data_source=(found[0].get("source") if found else None),
                   newest_reading_minutes_ago=places_data.LAST_INFO["newest_reading_minutes_ago"],
                   tiger_data_error=places_data.LAST_ERROR["message"])


@api.get("/me")
def me():
    u = session.get("user")
    return jsonify(user=({"name": u["name"], "email": u["email"]} if u else None))


@api.get("/places")
def places():
    return jsonify(places=places_data.get_places(request.args.get("q", ""),
                                                 request.args.get("lat"), request.args.get("lng")))


@api.post("/ask")
def ask():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    if not message:
        return jsonify(error="empty_message", reply="", place_id=None), 400
    history = data.get("history") if isinstance(data.get("history"), list) else []
    loc = data.get("location") if isinstance(data.get("location"), dict) else {}
    result = chat.ask(message, history, places_data.get_places("", loc.get("lat"), loc.get("lng")))
    return jsonify(reply=result["reply"], place_id=result["place_id"], error=result["error"])


@api.post("/report")
def report():
    data = request.get_json(silent=True) or {}
    ok = places_data.report_queue(str(data.get("place_id", "")), str(data.get("level", "")))
    return jsonify(ok=ok), (200 if ok else 400)
