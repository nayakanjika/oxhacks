"""Q-rious simulated live queue feed for Tiger Data.

Muhammed's seeded history stops at the time it was created, so the app sees "old" queues.
This script (1) fills the gap from the newest reading up to now, then (2) adds one new
reading per location every 2 minutes, shaped like each location's usual rush hours.

Run it in a second terminal and leave it running during the demo:
    python3 simulate_feed.py
Stop it with Control + C. It never prints the connection string.
"""
import os
import random
import time
from datetime import datetime, timedelta, timezone

import psycopg2
from dotenv import load_dotenv

load_dotenv()
URL = (os.getenv("TIGER_DATABASE_URL") or "").strip()
if not URL:
    raise SystemExit("TIGER_DATABASE_URL is not in your .env file.")

STEP = timedelta(minutes=2)


def next_value(prev, usual):
    """Move gently from the last count toward what is usual for this hour, with a little noise."""
    target = 0.7 * prev + 0.3 * usual + random.uniform(-1.2, 1.2)
    return max(0, int(round(target)))


def connect():
    return psycopg2.connect(URL, connect_timeout=8)


def run_once(conn):
    cur = conn.cursor()
    cur.execute("SELECT id FROM locations ORDER BY id")
    ids = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT location_id, EXTRACT(hour FROM time AT TIME ZONE 'Europe/London')::int, AVG(people_count) "
                "FROM queue_counts GROUP BY 1, 2")
    usual = {}
    for lid, hr, avg in cur.fetchall():
        usual[(lid, int(hr))] = float(avg)
    cur.execute("SELECT DISTINCT ON (location_id) location_id, people_count, time FROM queue_counts "
                "WHERE time <= now() ORDER BY location_id, time DESC")
    last = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    now = datetime.now(timezone.utc)
    added = 0
    for lid in ids:
        prev, t = last.get(lid, (3, now - STEP))
        t = t + STEP
        while t <= now:
            hour = t.astimezone(timezone(timedelta(hours=1))).hour  # close enough to London for a simulation
            prev = next_value(prev, usual.get((lid, hour), prev))
            cur.execute("INSERT INTO queue_counts (time, location_id, people_count) VALUES (%s, %s, %s)", (t, lid, prev))
            t += STEP
            added += 1
    conn.commit()
    return added


if __name__ == "__main__":
    print("Simulated feed running. Press Control + C to stop.")
    while True:
        try:
            conn = connect()
            try:
                n = run_once(conn)
            finally:
                conn.close()
            print(datetime.now().strftime("%H:%M:%S"), "added", n, "readings")
        except Exception as err:
            print("Problem:", type(err).__name__, str(err)[:120])
        time.sleep(60)
