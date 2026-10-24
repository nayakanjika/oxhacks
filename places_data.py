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

# Queue reports from the "Report a queue" button, kept in memory only
# (they reset when the server restarts). Replace with a Tiger Data insert.
_REPORTS = {}

_LEVELS = {  # level -> (people in queue, wait in minutes)
    "short": (2, 2),
    "medium": (6, 5),
    "long": (12, 12),
}


def get_places(query=""):
    """Return the list of places. `query` is the user's search text; for now we
    return everything and the screens filter it."""
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


def report_queue(place_id, level):
    """Save a crowd-sourced queue report. Returns True if the place exists."""
    if level not in _LEVELS or not any(p["id"] == place_id for p in SAMPLE_PLACES):
        return False
    _REPORTS[place_id] = _LEVELS[level]
    return True
