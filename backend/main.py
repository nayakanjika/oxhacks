"""
Q-rious backend (FastAPI + Tiger Data + Gemini)

Run locally:   uvicorn main:app --reload
Then open:     http://127.0.0.1:8000/docs   (try every endpoint from the browser)
"""
import math
import os
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()
DATABASE_URL = os.environ["DATABASE_URL"]           # from Tiger Data dashboard
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")   # from Google AI Studio
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
# How much Gemini "thinks" before answering. "low" is much faster than the default.
# Set GEMINI_THINKING= (empty) in .env if your model rejects it.
GEMINI_THINKING = os.environ.get("GEMINI_THINKING", "low")

app = FastAPI(title="Q-rious API")
app.add_middleware(  # lets the frontend (different port/domain) call this API
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


_conn = None
_db_lock = threading.RLock()


@contextmanager
def db():
    """
    One shared database connection, reused for every request (opening a new secure
    connection to the cloud each time was the slowest part). Reconnects if it drops.
    """
    global _conn
    with _db_lock:
        if _conn is None or _conn.closed or _conn.broken:
            _conn = psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=True)
        yield _conn


_gemini_client = None


def gemini():
    """Shared Gemini client that gives up after 10 seconds instead of hanging."""
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(api_key=GEMINI_API_KEY,
                                      http_options={"timeout": 12_000})  # milliseconds
    return _gemini_client


def ask_gemini(contents, **config):
    """Every Gemini call goes through here, with the fast thinking level applied."""
    if GEMINI_THINKING:
        config["thinking_config"] = {"thinking_level": GEMINI_THINKING}
    return gemini().models.generate_content(model=GEMINI_MODEL, contents=contents,
                                            config=config or None)


# ---------- helpers ----------

def distance_km(lat1, lng1, lat2, lng2):
    """Straight-line distance between two points (haversine formula)."""
    r = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


_history_cache = {}  # location_id -> (time fetched, data)


def slot_history(cur, loc):
    """
    Average queue size for each 15-minute slot of the day (last 14 days).
    History changes slowly, so we keep it in memory for 5 minutes.
    """
    cached = _history_cache.get(loc["id"])
    if cached and time.time() - cached[0] < 300:
        return cached[1]
    data = _slot_history_from_db(cur, loc)
    _history_cache[loc["id"]] = (time.time(), data)
    return data


def _slot_history_from_db(cur, loc):
    cur.execute(
        """SELECT EXTRACT(HOUR FROM bucket)::INT * 60
                + (EXTRACT(MINUTE FROM bucket)::INT / 15) * 15 AS minute_of_day,
                  avg(avg_people) AS hist
           FROM queue_5min
           WHERE location_id = %s AND bucket > now() - INTERVAL '14 days'
           GROUP BY minute_of_day""",
        (loc["id"],),
    )
    return {r["minute_of_day"]: float(r["hist"]) for r in cur.fetchall()}


def now_slot():
    now = datetime.now(timezone.utc)
    return now.hour * 60 + (now.minute // 15) * 15


def queue_level(people):
    """Label used on the map pins and cards: Short / Medium / Long."""
    if people <= 4:
        return "Short"
    if people <= 9:
        return "Medium"
    return "Long"


def current_status(cur, loc, history=None):
    """
    Queue right now. Uses a live head count from the last 2 minutes if there is one;
    otherwise falls back to the usual queue for this time of day (marked live=false).
    """
    cur.execute(
        """SELECT people_count, time FROM queue_counts
           WHERE location_id = %s AND time > now() - INTERVAL '2 minutes'
           ORDER BY time DESC LIMIT 1""",
        (loc["id"],),
    )
    row = cur.fetchone()
    if row:
        people = row["people_count"]
    else:
        history = history if history is not None else slot_history(cur, loc)
        people = round(history.get(now_slot(), 0))
    wait_mins = round(people * loc["secs_per_person"] / 60, 1)
    return {"people": people, "wait_mins": wait_mins, "live": row is not None,
            "level": queue_level(people)}


def arrival_estimate(loc, now_people, prediction, walk_mins):
    """
    What the queue will look like WHEN YOU GET THERE (screen 2: "When you arrive ~16 min"),
    plus a range, the trend, and a plain-English verdict.
    """
    points = [(0, now_people)] + [(p["minutes_ahead"], p["people"]) for p in prediction]
    t = min(max(walk_mins, 0), 60)
    people = now_people
    for (t0, p0), (t1, p1) in zip(points, points[1:]):
        if t0 <= t <= t1:
            people = p0 + (p1 - p0) * (t - t0) / (t1 - t0)
            break
    people = max(0, round(people))
    wait = round(people * loc["secs_per_person"] / 60)

    change = prediction[0]["people"] - now_people if prediction else 0
    trend = "rising" if change > 1 else "falling" if change < -1 else "steady"
    level = queue_level(people)
    if level == "Short":
        verdict, reason = "Go now", "The queue is short."
    elif level == "Long" and trend == "rising":
        verdict, reason = "Skip it", "The queue is getting longer."
    elif trend == "falling":
        verdict, reason = "Wait a bit", "The queue is getting shorter."
    else:
        verdict, reason = "Worth the trip", "The queue is steady."
    return {
        "people_on_arrival": people,
        "wait_on_arrival_mins": wait,
        "wait_range_mins": [max(0, round(wait * 0.8)), round(wait * 1.2) + 1],
        "level_on_arrival": level,
        "trend": trend,
        "verdict": verdict,
        "verdict_reason": reason,
    }


def predict(cur, loc, now_people, history=None):
    """
    Simple, explainable prediction for the next hour in 15-minute steps:
    blend the CURRENT queue with the HISTORICAL average for that time of day.
    Weight shifts from 'now' towards 'history' the further ahead we look.
    """
    history = history if history is not None else slot_history(cur, loc)
    now_min = now_slot()
    out = []
    for step in range(1, 5):  # +15, +30, +45, +60 minutes
        m = (now_min + step * 15) % 1440
        hist = history.get(m, now_people)
        w = step / 4                       # 0.25 -> 1.0
        people = (1 - w) * now_people + w * hist
        out.append({
            "minutes_ahead": step * 15,
            "people": round(people, 1),
            "wait_mins": round(people * loc["secs_per_person"] / 60, 1),
        })
    return out


# ---------- request bodies ----------

class CountIn(BaseModel):
    location_id: int
    people_count: int

class EventIn(BaseModel):
    location_id: int
    ticket_id: str
    event: str  # 'join' or 'served'

class UserIn(BaseModel):
    email: str
    name: str | None = None

class AlertIn(BaseModel):
    email: str
    location_id: int
    max_wait_mins: int

class ChatIn(BaseModel):
    message: str
    lat: float = 51.7603
    lng: float = -1.2630

class SearchIn(BaseModel):
    query: str                  # whatever the user typed, e.g. "best coffee shop nearby"
    lat: float = 51.7603
    lng: float = -1.2630

class SearchFilters(BaseModel):
    """What Gemini extracts from the user's search text."""
    category: str | None        # one of our categories, or null
    tag: str | None             # e.g. "coconut milk", or null
    max_km: float               # how far they're willing to go
    sort_by: str                # "total_time", "wait", or "distance"


# ---------- endpoints ----------

@app.get("/")
def health():
    return {"ok": True, "service": "Q-rious"}


WALK_KMH = 5  # average walking speed


def describe_place(cur, loc, lat, lng):
    """Everything a card / pin / place sheet needs for one place."""
    d = distance_km(lat, lng, loc["lat"], loc["lng"])
    walk_mins = round(d / WALK_KMH * 60)
    history = slot_history(cur, loc)
    status = current_status(cur, loc, history)
    prediction = predict(cur, loc, status["people"], history)
    arrival = arrival_estimate(loc, status["people"], prediction, walk_mins)
    return {**loc, **status, **arrival, "prediction": prediction,
            "distance_km": round(d, 2), "walk_mins": walk_mins,
            # total time = walk there + predicted queue when you arrive
            "total_mins": walk_mins + arrival["wait_on_arrival_mins"]}


@app.get("/locations")
def list_locations(lat: float = 51.7603, lng: float = -1.2630, max_km: float = 2.0,
                   category: str | None = None, tag: str | None = None,
                   max_walk_mins: int | None = None):
    """
    Nearby places, best first (shortest walk + predicted queue on arrival).
    max_walk_mins = the "How far will you walk? 5 / 10 / 15 min" buttons.
    """
    if max_walk_mins is not None:
        max_km = max_walk_mins * WALK_KMH / 60
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM locations")
        results = []
        for loc in cur.fetchall():
            if distance_km(lat, lng, loc["lat"], loc["lng"]) > max_km:
                continue
            if category and loc["category"] != category:
                continue
            if tag and tag.lower() not in [t.lower() for t in loc["menu_tags"]]:
                continue
            results.append(describe_place(cur, loc, lat, lng))
        results.sort(key=lambda r: r["total_mins"])
        for i, r in enumerate(results):
            r["best_option"] = i == 0
        return results


@app.get("/locations/{location_id}")
def location_detail(location_id: int, lat: float = 51.7603, lng: float = -1.2630):
    """One place (screen 2): queue now, queue when you arrive, verdict, prediction, chart data."""
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM locations WHERE id = %s", (location_id,))
        loc = cur.fetchone()
        if not loc:
            raise HTTPException(404, "Location not found")
        place = describe_place(cur, loc, lat, lng)
        cur.execute(
            """SELECT bucket, avg_people FROM queue_5min
               WHERE location_id = %s AND bucket > now() - INTERVAL '3 hours'
               ORDER BY bucket""",
            (location_id,),
        )
        history = cur.fetchall()
        return {**place, "history": history}


@app.post("/counts")
def add_count(body: CountIn):
    """The camera script calls this every ~10 seconds."""
    with db() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO queue_counts (location_id, people_count) VALUES (%s, %s)",
                    (body.location_id, body.people_count))
    return {"saved": True}


@app.post("/events")
def add_event(body: EventIn):
    """QR scan: 'join' then 'served'. On 'served' we re-learn the real service time."""
    if body.event not in ("join", "served"):
        raise HTTPException(400, "event must be 'join' or 'served'")
    with db() as conn, conn.cursor() as cur:
        cur.execute("INSERT INTO queue_events (location_id, ticket_id, event) VALUES (%s, %s, %s)",
                    (body.location_id, body.ticket_id, body.event))
        if body.event == "served":
            cur.execute(
                """SELECT EXTRACT(EPOCH FROM s.time - j.time) AS waited
                   FROM queue_events j JOIN queue_events s
                     ON j.ticket_id = s.ticket_id AND s.event = 'served'
                   WHERE j.event = 'join' AND j.location_id = %s AND j.ticket_id = %s""",
                (body.location_id, body.ticket_id),
            )
            row = cur.fetchone()
            if row:
                return {"saved": True, "you_waited_mins": round(row["waited"] / 60, 1)}
    return {"saved": True}


@app.post("/users")
def guest_signup(body: UserIn):
    """Guest login: just an email, used for notifications."""
    with db() as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO users (email, name) VALUES (%s, %s)
               ON CONFLICT (email) DO UPDATE SET name = COALESCE(EXCLUDED.name, users.name)
               RETURNING id, email, name""",
            (body.email.strip().lower(), body.name),
        )
        return cur.fetchone()


@app.post("/alerts")
def create_alert(body: AlertIn):
    """'Tell me when the queue is under N minutes.'"""
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM users WHERE email = %s", (body.email.strip().lower(),))
        user = cur.fetchone()
        if not user:
            raise HTTPException(404, "Sign up first via /users")
        cur.execute(
            "INSERT INTO alerts (user_id, location_id, max_wait_mins) VALUES (%s, %s, %s) RETURNING id",
            (user["id"], body.location_id, body.max_wait_mins),
        )
        return {"alert_id": cur.fetchone()["id"]}


@app.get("/alerts/due")
def alerts_due():
    """Alerts whose queue is now short enough. Frontend polls this (or send emails from here)."""
    with db() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT a.id AS alert_id, a.max_wait_mins, u.email, l.* FROM alerts a
               JOIN users u ON u.id = a.user_id JOIN locations l ON l.id = a.location_id
               WHERE a.active"""
        )
        due = []
        for row in cur.fetchall():
            status = current_status(cur, row)
            if status["wait_mins"] <= row["max_wait_mins"]:
                due.append({"alert_id": row["alert_id"], "email": row["email"],
                            "location": row["name"], "wait_mins": status["wait_mins"]})
        return due


def keyword_filters(query: str, categories: list[str], tags: list[str]) -> SearchFilters:
    """Backup if Gemini is down or slow: simple keyword matching."""
    q = query.lower()
    synonyms = {"coffee": ["coffee", "cafe", "café", "latte", "espresso", "cappuccino"],
                "food": ["food", "pizza", "lunch", "dinner", "eat"],
                "library": ["library", "study", "quiet"],
                "printer": ["print", "printer"]}
    category = next((c for c in categories
                     if any(w in q for w in synonyms.get(c, [c]))), None)
    tag = next((t for t in tags if t.lower() in q), None)
    return SearchFilters(category=category, tag=tag, max_km=2.0, sort_by="total_time")


@app.post("/search")
def search(body: SearchIn):
    """
    Search bar: "best coffee shop nearby", "coconut milk latte within 10 min walk"...
    1. Gemini turns the text into filters (category, tag, distance, sort).
    2. We return ALL matching places from our database with live queue times.
    3. A one-line summary of the top result.
    """
    with db() as conn, conn.cursor() as cur:
        cur.execute("SELECT DISTINCT category FROM locations")
        categories = [r["category"] for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT unnest(menu_tags) AS tag FROM locations")
        tags = [r["tag"] for r in cur.fetchall()]

    filters, used_gemini = None, False
    if GEMINI_API_KEY:
        try:
            prompt = (
                "Turn this search into filters for a queue-time app.\n"
                f"Allowed categories: {categories} (use null if none fits).\n"
                f"Allowed tags: {tags} (use null if none is mentioned).\n"
                "max_km: 0.5 for 'very close', 1 for 'nearby'/'walking distance', "
                "2 if not mentioned; 10 minutes walking is about 0.8 km.\n"
                "sort_by: 'wait' if they care about the shortest queue, 'distance' if closest, "
                "otherwise 'total_time'.\n\n"
                f"Search: {body.query}"
            )
            resp = ask_gemini(prompt, response_mime_type="application/json",
                              response_schema=SearchFilters)
            filters, used_gemini = resp.parsed, True
        except Exception as e:  # never let the search bar break during the demo
            print("Gemini filter step failed, using keywords:", e)
    if filters is None:
        filters = keyword_filters(body.query, categories, tags)

    results = list_locations(lat=body.lat, lng=body.lng, max_km=filters.max_km,
                             category=filters.category, tag=filters.tag)
    # nothing in range? widen the search instead of showing an empty page
    if not results:
        results = list_locations(lat=body.lat, lng=body.lng, max_km=5.0,
                                 category=filters.category, tag=filters.tag)
    sort_key = {"wait": "wait_mins", "distance": "distance_km"}.get(filters.sort_by, "total_mins")
    results.sort(key=lambda r: r[sort_key])

    # Instant summary from our own numbers (a second Gemini call here doubled the wait).
    # The longer Gemini explanation lives in /recommend (screen 4).
    summary = None
    if results:
        best = results[0]
        summary = (f"{best['name']} is your best bet: a {best['walk_mins']} min walk and about "
                   f"{best['wait_on_arrival_mins']} min queue when you arrive.")

    return {
        "query": body.query,
        "filters": filters.model_dump(),   # show these as chips in the UI ("coffee", "≤1 km")
        "used_gemini": used_gemini,
        "summary": summary,
        "count": len(results),
        "results": results,                # ALL matching places, best first
    }


class RecommendIn(BaseModel):
    lat: float = 51.7603
    lng: float = -1.2630
    from_location_id: int | None = None   # the place they were looking at (e.g. Blue Door Café)
    tag: str | None = None                # e.g. "coconut milk"
    category: str | None = None           # e.g. "coffee"
    max_walk_mins: int = 10               # the 5 / 10 / 15 min buttons


@app.post("/recommend")
def recommend(body: RecommendIn):
    """
    Screens 3 + 4: "Other options" and "Your best option".
    Returns the best place, the alternatives, how many minutes you save compared with
    the place you were looking at, and a short Gemini explanation.
    """
    options = list_locations(lat=body.lat, lng=body.lng, category=body.category,
                             tag=body.tag, max_walk_mins=body.max_walk_mins)
    if not options:
        raise HTTPException(404, "Nothing within that walking distance. Try a longer walk.")
    best = options[0]

    original, saved = None, None
    if body.from_location_id is not None:
        with db() as conn, conn.cursor() as cur:
            cur.execute("SELECT * FROM locations WHERE id = %s", (body.from_location_id,))
            loc = cur.fetchone()
            if loc:
                original = describe_place(cur, loc, body.lat, body.lng)
                saved = max(0, original["total_mins"] - best["total_mins"])

    explanation = (f"{best['name']} is {best['walk_mins']} min away and should have about "
                   f"{best['people_on_arrival']} people queuing when you arrive.")
    if GEMINI_API_KEY:
        try:
            facts = (f"Best: {best['name']}, {best['walk_mins']} min walk, "
                     f"{best['people']} people now, about {best['people_on_arrival']} on arrival "
                     f"(trend {best['trend']}).")
            if original:
                facts += (f" They were looking at {original['name']}: {original['walk_mins']} min "
                          f"walk, {original['people']} people now, trend {original['trend']}. "
                          f"Choosing the best option saves {saved} minutes.")
            resp = ask_gemini(
                (f"{facts}\nIn 2 short friendly sentences, explain why the best "
                          "option is better. Use only these facts."),
            )
            explanation = resp.text.strip()
        except Exception as e:
            print("Gemini explanation failed:", e)

    return {
        "best": best,
        "alternatives": options[1:],
        "compared_with": original["name"] if original else None,
        "time_saved_mins": saved,      # "You save 7 min"
        "explanation": explanation,    # the Gemini box
    }


@app.post("/chat")
def chat(body: ChatIn):
    """Gemini chatbot that answers using OUR live queue data."""
    if not GEMINI_API_KEY:
        raise HTTPException(500, "GEMINI_API_KEY not set")

    places = list_locations(lat=body.lat, lng=body.lng, max_km=3.0)
    context = "\n".join(
        f"- {p['name']} ({p['category']}): {p['wait_mins']} min queue, "
        f"{p['walk_mins']} min walk, serves: {', '.join(p['menu_tags']) or 'n/a'}"
        for p in places
    )
    prompt = (
        "You are Q-rious, a friendly assistant that helps students avoid long queues.\n"
        "Use ONLY the live data below. Recommend the best option considering walk time "
        "plus queue time, and keep answers to 2-3 short sentences.\n\n"
        f"Live data:\n{context}\n\nUser: {body.message}"
    )
    reply = ask_gemini(prompt)
    return {"reply": reply.text}
