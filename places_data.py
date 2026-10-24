"""Q-rious: where the app gets its places and queue numbers.

TIGER DATA TEAMMATE: this is YOUR file. Right now get_places() returns the
SAMPLE places below. Replace the body of get_places() with a query to Tiger
Data and return a list of dicts with the SAME field names. Everything else
(the screens, the chat, the map) reads from here, so nothing else needs to change.

Fields each place needs:
    id, place, category, walk_minutes, queue_now, queue_on_arrival,
    wait_minutes, trend ("rising" | "dropping" | "steady"), sells (list)
Nice to have:
    wait_low, wait_high (the prediction range), lat, lng, source
    ("sample" or "live"), by_hour (average wait for each hour of the day)

map_x / map_y only place the pins on the placeholder map. The real Google Map
uses lat and lng instead.
"""

import math


def _sample_by_hour(base, peak):
    """Sample average wait (minutes) for each hour 0 to 23: a morning rush around
    09:00 and a lunch rush around 13:00. Tiger Data replaces this with real history."""
    return [int(round(base + peak * math.exp(-((h - 9) ** 2) / 4.0)
                      + 0.8 * peak * math.exp(-((h - 13) ** 2) / 4.0))) for h in range(24)]


SAMPLE_PLACES = [
    {
        "id": "blue-door", "place": "Blue Door Café", "category": "Café",
        "walk_minutes": 2, "queue_now": 14, "queue_on_arrival": 13, "wait_minutes": 14,
        "wait_low": 12, "wait_high": 17, "trend": "rising",
        "sells": ["coffee", "coconut milk", "oat milk"],
        "by_hour": _sample_by_hour(3, 12),
        "lat": 51.7520, "lng": -1.2577, "map_x": 44, "map_y": 34, "source": "sample",
    },
    {
        "id": "corner-roast", "place": "Corner Roast", "category": "Café",
        "walk_minutes": 6, "queue_now": 6, "queue_on_arrival": 3, "wait_minutes": 3,
        "wait_low": 2, "wait_high": 5, "trend": "dropping",
        "sells": ["coffee", "coconut milk", "oat milk"],
        "by_hour": _sample_by_hour(1, 6),
        "lat": 51.7535, "lng": -1.2540, "map_x": 70, "map_y": 22, "source": "sample",
    },
    {
        "id": "oat-and-bean", "place": "Oat & Bean", "category": "Café",
        "walk_minutes": 9, "queue_now": 6, "queue_on_arrival": 5, "wait_minutes": 3,
        "wait_low": 2, "wait_high": 6, "trend": "dropping",
        "sells": ["coffee", "coconut milk", "oat milk"],
        "by_hour": _sample_by_hour(2, 6),
        "lat": 51.7490, "lng": -1.2610, "map_x": 22, "map_y": 36, "source": "sample",
    },
    {
        "id": "quad-coffee", "place": "Quad Coffee", "category": "Café",
        "walk_minutes": 10, "queue_now": 4, "queue_on_arrival": 7, "wait_minutes": 5,
        "wait_low": 4, "wait_high": 8, "trend": "rising",
        "sells": ["coffee", "coconut milk"],
        "by_hour": _sample_by_hour(2, 7),
        "lat": 51.7555, "lng": -1.2500, "map_x": 80, "map_y": 38, "source": "sample",
    },
    {
        "id": "tillys", "place": "Tilly's Tea Room", "category": "Tea room",
        "walk_minutes": 3, "queue_now": 2, "queue_on_arrival": 2, "wait_minutes": 2,
        "wait_low": 1, "wait_high": 3, "trend": "steady",
        "sells": ["tea", "cake"],
        "by_hour": _sample_by_hour(1, 3),
        "lat": 51.7510, "lng": -1.2560, "map_x": 56, "map_y": 28, "source": "sample",
    },
]

# ---------------------------------------------------------------------------
# Tiger Data (PostgreSQL). Used when TIGER_DATABASE_URL is set in .env and the
# tables `places` and `queue_readings` exist. Otherwise the sample places above
# are used, so the app never breaks.
#
#   places(id, name, category, lat, lng, sells)
#   queue_readings(time, place_id, queue_count)
# ---------------------------------------------------------------------------
import os
import time as _time
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

try:
    from zoneinfo import ZoneInfo
    _LONDON = ZoneInfo("Europe/London")
except Exception:  # pragma: no cover
    _LONDON = None

ORIGIN = (51.7534, -1.2540)   # "You are here" for walk times (central Oxford) until we use the phone's location
MIN_PER_PERSON = 0.8          # how long each person in the queue adds to the wait
_CACHE = {"at": 0, "places": None}
LAST_ERROR = {"message": ""}   # shown by /api/health so problems are easy to spot

# Queue reports from the "Report a queue" button when there is no database.
_REPORTS = {}
_LEVELS = {  # level -> (people in queue, wait in minutes)
    "short": (2, 2),
    "medium": (6, 5),
    "long": (12, 12),
}


def db_configured():
    return bool((os.getenv("TIGER_DATABASE_URL") or "").strip())


def _connect():
    import psycopg2
    return psycopg2.connect(os.environ["TIGER_DATABASE_URL"].strip(), connect_timeout=5)


def _walk_minutes(lat, lng):
    """Straight-line distance from ORIGIN, scaled up for real streets, at about 80 m a minute."""
    import math as m
    r = 6371000.0
    p1, p2 = m.radians(ORIGIN[0]), m.radians(lat)
    dp, dl = p2 - p1, m.radians(lng - ORIGIN[1])
    a = m.sin(dp / 2) ** 2 + m.cos(p1) * m.cos(p2) * m.sin(dl / 2) ** 2
    metres = 2 * r * m.asin(m.sqrt(a)) * 1.25
    return max(1, int(round(metres / 80.0)))


def _london_now():
    return datetime.now(_LONDON) if _LONDON else datetime.now()


def _build_places(place_rows, latest, earlier, hourly, now=None):
    """Pure function (easy to test): turns database rows into the list the app uses.

    place_rows : [(id, name, category, lat, lng, sells)]
    latest     : {place_id: (queue_count, reading_time)}
    earlier    : {place_id: queue_count about 30 minutes ago}
    hourly     : {place_id: {hour: average queue_count}}
    """
    now = now or _london_now()
    out = []
    for pid, name, category, lat, lng, sells in place_rows:
        if pid not in latest:
            continue
        people, read_at = latest[pid]
        walk = _walk_minutes(lat, lng)
        # Trend: compare with about 30 minutes ago.
        before = earlier.get(pid, people)
        trend = "rising" if people - before >= 2 else "dropping" if before - people >= 2 else "steady"
        # Past averages for every hour of the day (in people), with gaps filled.
        hours = hourly.get(pid, {})
        avg_all = (sum(hours.values()) / len(hours)) if hours else people
        by_hour_people = [hours.get(h, avg_all) for h in range(24)]
        # Prediction: blend the queue right now with what is usual at the hour you will arrive.
        arrive_hour = (now.hour + int((now.minute + walk) // 60)) % 24
        expected = int(round(0.5 * people + 0.5 * by_hour_people[arrive_hour]))
        wait = int(round(expected * MIN_PER_PERSON))
        age_min = None
        try:
            ref = read_at.astimezone(now.tzinfo) if getattr(read_at, "tzinfo", None) else read_at
            age_min = (now - ref).total_seconds() / 60.0
        except Exception:
            pass
        out.append({
            "id": pid, "place": name, "category": category or "Café",
            "walk_minutes": walk, "queue_now": int(people), "queue_on_arrival": expected,
            "wait_minutes": wait, "wait_low": max(0, int(round(wait * 0.75))),
            "wait_high": int(round(wait * 1.3)) + 1, "trend": trend,
            "sells": list(sells or []),
            "by_hour": [int(round(v * MIN_PER_PERSON)) for v in by_hour_people],
            "lat": lat, "lng": lng,
            # "live" only if the newest reading is fresh; otherwise be honest and say sample.
            "source": "live" if age_min is not None and age_min <= 30 else "sample",
        })
    return out


def _load_from_db():
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, name, category, lat, lng, sells FROM places")
        place_rows = cur.fetchall()
        cur.execute("SELECT DISTINCT ON (place_id) place_id, queue_count, time "
                    "FROM queue_readings ORDER BY place_id, time DESC")
        latest = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
        cur.execute("SELECT DISTINCT ON (place_id) place_id, queue_count FROM queue_readings "
                    "WHERE time <= now() - interval '30 minutes' ORDER BY place_id, time DESC")
        earlier = {r[0]: r[1] for r in cur.fetchall()}
        cur.execute("SELECT place_id, EXTRACT(hour FROM time AT TIME ZONE 'Europe/London')::int, AVG(queue_count) "
                    "FROM queue_readings GROUP BY 1, 2")
        hourly = {}
        for pid, hr, avg in cur.fetchall():
            hourly.setdefault(pid, {})[int(hr)] = float(avg)
        return place_rows, latest, earlier, hourly
    finally:
        conn.close()


def _sample_places():
    places = []
    for p in SAMPLE_PLACES:
        p = dict(p)
        report = _REPORTS.get(p["id"])
        if report:
            people, wait = report
            p.update(queue_now=people, queue_on_arrival=people, wait_minutes=wait,
                     wait_low=max(0, wait - 2), wait_high=wait + 3)
        places.append(p)
    return places


def get_places(query=""):
    """The one function the app calls for places. Tiger Data if connected, else sample places."""
    if not db_configured():
        return _sample_places()
    if _CACHE["places"] is not None and _time.time() - _CACHE["at"] < 20:
        return _CACHE["places"]
    try:
        places = _build_places(*_load_from_db())
        if not places:
            raise RuntimeError("Tiger Data connected but no places with queue readings were found")
        _CACHE.update(at=_time.time(), places=places)
        LAST_ERROR["message"] = ""
        return places
    except Exception as err:  # never break the app: fall back to sample data
        LAST_ERROR["message"] = type(err).__name__ + ": " + str(err)[:200]
        return _sample_places()


def report_queue(place_id, level):
    """Save a crowd-sourced queue report. Returns True if it was saved."""
    if level not in _LEVELS:
        return False
    people = _LEVELS[level][0]
    if db_configured():
        try:
            conn = _connect()
            try:
                cur = conn.cursor()
                cur.execute("SELECT 1 FROM places WHERE id = %s", (place_id,))
                if not cur.fetchone():
                    return False
                cur.execute("INSERT INTO queue_readings (time, place_id, queue_count) VALUES (now(), %s, %s)",
                            (place_id, people))
                conn.commit()
            finally:
                conn.close()
            _CACHE["places"] = None
            return True
        except Exception as err:
            LAST_ERROR["message"] = type(err).__name__ + ": " + str(err)[:200]
            return False
    if not any(p["id"] == place_id for p in SAMPLE_PLACES):
        return False
    _REPORTS[place_id] = _LEVELS[level]
    return True
