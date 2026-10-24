-- Queueless database schema (run this once in the Tiger Data SQL editor)

-- Places people queue at (cafés, library, printers, pizza line...)
CREATE TABLE IF NOT EXISTS locations (
    id                  SERIAL PRIMARY KEY,
    name                TEXT NOT NULL,
    category            TEXT NOT NULL,          -- 'coffee', 'library', 'printer', 'food'...
    lat                 DOUBLE PRECISION NOT NULL,
    lng                 DOUBLE PRECISION NOT NULL,
    menu_tags           TEXT[] DEFAULT '{}',    -- e.g. {'coconut milk','oat milk','vegan'}
    secs_per_person     INT DEFAULT 60          -- default service time, updated from QR data
);

-- Camera head counts: one row every ~10 seconds per location (time-series!)
CREATE TABLE IF NOT EXISTS queue_counts (
    time            TIMESTAMPTZ NOT NULL DEFAULT now(),
    location_id     INT NOT NULL REFERENCES locations(id),
    people_count    INT NOT NULL
);
SELECT create_hypertable('queue_counts', by_range('time'), if_not_exists => TRUE);

-- QR scans: 'join' when someone joins the queue, 'served' when they reach the front
CREATE TABLE IF NOT EXISTS queue_events (
    time            TIMESTAMPTZ NOT NULL DEFAULT now(),
    location_id     INT NOT NULL REFERENCES locations(id),
    ticket_id       TEXT NOT NULL,              -- random id stored on the person's phone
    event           TEXT NOT NULL CHECK (event IN ('join', 'served'))
);
SELECT create_hypertable('queue_events', by_range('time'), if_not_exists => TRUE);

-- Users: guest sign-up with email only (no passwords to keep it simple and safe)
CREATE TABLE IF NOT EXISTS users (
    id          SERIAL PRIMARY KEY,
    email       TEXT UNIQUE NOT NULL,
    name        TEXT,
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- "Tell me when the queue drops below N minutes"
CREATE TABLE IF NOT EXISTS alerts (
    id              SERIAL PRIMARY KEY,
    user_id         INT REFERENCES users(id),
    location_id     INT REFERENCES locations(id),
    max_wait_mins   INT NOT NULL,
    active          BOOLEAN DEFAULT TRUE
);

-- Continuous aggregate: 5-minute averages, kept up to date automatically.
-- This powers the fast dashboard AND the prediction (show this off for the Tiger Data prize).
CREATE MATERIALIZED VIEW IF NOT EXISTS queue_5min
WITH (timescaledb.continuous) AS
SELECT location_id,
       time_bucket('5 minutes', time) AS bucket,
       avg(people_count)::FLOAT        AS avg_people,
       max(people_count)               AS max_people
FROM queue_counts
GROUP BY location_id, bucket;

SELECT add_continuous_aggregate_policy('queue_5min',
    start_offset      => INTERVAL '1 day',
    end_offset        => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute');

-- Demo locations (change to real places near the Maths Institute)
INSERT INTO locations (name, category, lat, lng, menu_tags, secs_per_person) VALUES
 ('OxHack Food Line',      'food',    51.7605, -1.2633, '{pizza,vegan}',              20),
 ('Maths Institute Café',  'coffee',  51.7603, -1.2630, '{coconut milk,oat milk}',    75),
 ('Jericho Coffee Spot',   'coffee',  51.7590, -1.2680, '{coconut milk,almond milk}', 60),
 ('Woodstock Rd Café',     'coffee',  51.7640, -1.2650, '{oat milk}',                 90),
 ('Radcliffe Science Library', 'library', 51.7590, -1.2560, '{}',                     30);
