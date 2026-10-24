"""Prints what is inside your Tiger Data database: table names, columns and 3 sample rows.
It never prints the connection string or password, so the output is safe to paste to Claude.
Run it with:  python3 check_db.py
"""
import os

import psycopg2
from dotenv import load_dotenv

load_dotenv()
url = (os.getenv("TIGER_DATABASE_URL") or "").strip()
if not url:
    raise SystemExit("TIGER_DATABASE_URL is not in your .env file.")

conn = psycopg2.connect(url, connect_timeout=8)
cur = conn.cursor()
cur.execute("""
    SELECT table_schema, table_name FROM information_schema.tables
    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
      AND table_schema NOT LIKE '\\_timescaledb%' AND table_schema NOT LIKE 'timescaledb%'
      AND table_schema NOT LIKE 'pg_toast%' AND table_type = 'BASE TABLE'
    ORDER BY 1, 2""")
tables = cur.fetchall()
if not tables:
    print("Connected, but there are no tables yet.")
for schema, table in tables:
    print("\n=== " + schema + "." + table + " ===")
    cur.execute("SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position", (schema, table))
    print("columns:", ", ".join(c + " (" + t + ")" for c, t in cur.fetchall()))
    try:
        cur.execute('SELECT * FROM "' + schema + '"."' + table + '" LIMIT 3')
        for row in cur.fetchall():
            print("  ", tuple(str(v)[:40] for v in row))
        cur.execute('SELECT count(*) FROM "' + schema + '"."' + table + '"')
        print("rows:", cur.fetchone()[0])
    except Exception as e:
        conn.rollback()
        print("  (could not read rows:", type(e).__name__ + ")")
conn.close()
