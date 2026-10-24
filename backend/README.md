# Queueless backend: step-by-step

Stack: **Python + FastAPI** (API) → **Tiger Data** (database) → **Gemini** (chatbot) → **Vultr** (hosting).
Why FastAPI: simplest Python web framework, and it gives you a free test page at `/docs`.

## Step 1: Install (10 min)
```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Step 2: Create the database on Tiger Data (15 min)
1. Sign up at tigerdata.com (use the MLH link/credits if they gave you one).
2. Create a new service (free tier is fine). Copy the **connection string** it shows you.
3. `cp .env.example .env` and paste the connection string into `DATABASE_URL`.
4. Open the service's **SQL editor**, paste all of `schema.sql`, and run it.
   - If the location names are wrong, edit the `INSERT INTO locations` lines.

## Step 3: Fake history so the prediction works (2 min)
```bash
python seed_demo_data.py
```
Gives 7 days of realistic data. Tell judges it's seeded, and show the REAL hackathon data on top.

## Step 4: Run the API (2 min)
```bash
uvicorn main:app --reload
```
Open http://127.0.0.1:8000/docs and click "Try it out" on each endpoint.

| Endpoint | Who uses it | What it does |
|---|---|---|
| `GET /locations?lat=..&lng=..&max_km=1&tag=coconut milk` | Map page | Nearby places, sorted by walk + queue time |
| `GET /locations/{id}` | Location page | Live wait, 1-hour prediction, recent chart data |
| `POST /counts` | Camera script | Saves a head count |
| `POST /events` | QR page | `join` / `served` scans → real wait times |
| `POST /users` | Login page | Guest sign-up with email |
| `POST /alerts` / `GET /alerts/due` | Notifications | "Tell me when it's under N minutes" |
| `POST /search` `{"query": "best coffee shop nearby", "lat": .., "lng": ..}` | Search bar | Gemini reads the text → returns ALL matching places, best first, plus a one-line recommendation |
| `POST /chat` | Chatbot | Gemini answers using the live queue data |

## Step 5: Gemini key (5 min)
Get a key at aistudio.google.com → put it in `.env` as `GEMINI_API_KEY`.
Check the current model name there; change `GEMINI_MODEL` if needed.

## Step 6: Camera counter (10 min)
```bash
python counter.py --location 1
```
Points the laptop webcam at a queue and sends the count every 10 seconds. Only the number leaves the laptop.

## Step 7: Give the frontend team the API
Tell them the base URL and send them the `/docs` page. They just call these endpoints with `fetch()`.

## Step 8: Deploy on Vultr (Sunday morning, ~1 hour)
1. Create a small Ubuntu server on Vultr (use the MLH credits).
2. SSH in, `git clone` your repo, repeat Step 1, create `.env`.
3. Run: `uvicorn main:app --host 0.0.0.0 --port 8000`
4. Give the frontend `http://YOUR_SERVER_IP:8000`. Mention Vultr in the Devpost write-up.

## Rules for yourself
- Never commit `.env` to GitHub (add it to `.gitignore`).
- Get each step working before starting the next.
- If something breaks, the error in the terminal tells you which line. Paste it to a teammate or to Claude.
