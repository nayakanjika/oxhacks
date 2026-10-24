"""
Fills the database with 7 days of realistic fake history so the prediction and charts
work straight away. Run once: python seed_demo_data.py
(Your REAL hackathon data is added on top by counter.py / QR scans.)
"""
import math
import os
import random
from datetime import datetime, timedelta, timezone

import psycopg
from dotenv import load_dotenv

load_dotenv()
conn = psycopg.connect(os.environ["DATABASE_URL"], autocommit=True)
cur = conn.cursor()
cur.execute("SELECT id, category FROM locations")
locations = cur.fetchall()

# busy peaks (hour of day) per category
PEAKS = {"coffee": [8.5, 11, 14], "food": [12.5, 18.5, 0], "library": [14, 20], "printer": [9, 16]}

now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
rows = []
for loc_id, cat in locations:
    t = now - timedelta(days=7)
    while t < now:
        hour = t.hour + t.minute / 60
        level = sum(10 * math.exp(-((hour - p) ** 2) / 0.5) for p in PEAKS.get(cat, [12]))
        people = max(0, round(level + random.gauss(0, 1.5)))
        rows.append((t, loc_id, people))
        t += timedelta(minutes=2)

with cur.copy("COPY queue_counts (time, location_id, people_count) FROM STDIN") as copy:
    for r in rows:
        copy.write_row(r)
conn.commit()
cur.execute("CALL refresh_continuous_aggregate('queue_5min', NULL, NULL)")
conn.commit()
print(f"Inserted {len(rows)} rows")
