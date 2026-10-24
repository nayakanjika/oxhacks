# Q-rious: setup notes

Satisfy your Q-riosity. A phone-first website built with Flask, HTML and CSS.

## Run it on your computer (Mac)

From the project folder, in the VS Code terminal:

```
python3 -m venv venv              # only the first time
source venv/bin/activate          # every time you open a new terminal
pip install -r requirements.txt   # only the first time
python3 app.py
```

Then open http://127.0.0.1:5001 in your browser. Save a file, refresh the page, and
you will see the change.

Stop the site with Control + C in the terminal.

## Seeing the phone version

In Chrome, right-click the page, choose Inspect, then click the small
phone-and-tablet icon (or press Cmd + Shift + M) and pick an iPhone.

## What is where

```
app.py               the control room: one route per page
templates/base.html  shared frame for every page (font, viewport, styles)
templates/index.html landing page (logo, tagline, guest / log in)
templates/login.html "coming soon" placeholder
templates/search.html where "Continue as guest" goes (teammates build here)
templates/search.html the app screen (map, sheets, chat, settings): just the frame
static/ui.js         all the app screen behaviour (screens, chat, voice, settings)
static/ui.css        styles for the app screen
static/ui-data.js    settings (demo on/off) and the SAMPLE places
static/style.css     colours, font and layout
static/logo.svg      Oxford blue logo
static/logo-white.svg white logo for dark backgrounds
```

## Adding a page

1. In app.py, copy one of the routes and change the address and template name.
2. Create the matching file in templates/ that starts with `{% extends "base.html" %}`.
3. Link to it with `{{ url_for('function_name') }}`.

## Changing the font

Change `--font-main` at the top of static/style.css, and the Google Fonts link in
templates/base.html. Tell the team first so two people do not edit the same lines.

## Colours

Oxford blue `#002147` and white. Queue lengths should be shown as a word plus an
icon (Short / Medium / Long), not only a colour, so it works for colour blindness.

## Secrets

Put API keys in a file called `.env` (it is ignored by Git). Never commit keys.

## The app screen (search.html)

Everything after "Continue as guest" is one screen. Panels slide up from the bottom.
The flow: search -> tap a pin -> place sheet -> "Too long? Find another" ->
alternatives (walking filter) -> recommendation -> "Take me there".

It runs on SAMPLE DATA at the moment (`demo: true` in static/ui-data.js). Every
sheet shows a small "Sample data" tag while that is on.

### Plugging in the real data (backend)
1. In static/ui-data.js set `demo: false`.
2. Make these routes return JSON (fields are listed at the top of ui-data.js):
   - `GET /api/places?q=coconut milk latte` -> `{ "places": [ ... ] }`
   - `POST /api/ask` with `{message, context}` -> `{ "reply": "...", "place_id": "..." }`
   - `POST /api/report` with `{place_id, level}` -> `{ "ok": true }`
3. If your field names differ, change ONLY `adaptPlace()` in static/ui.js.

### Plugging in the real Google Map
1. In static/ui-data.js set `realMap: true` (stops the placeholder map drawing).
2. Create the Google Map inside `<div id="map">`.
3. Listen for places and draw markers:
   `document.addEventListener("qrious:places", e => { /* e.detail = list of places */ })`
4. When a marker is clicked call `Qrious.select(place.id)` and the place sheet opens.

### Voice
`listen()` and `speak()` in static/ui.js use the browser's built-in voice tools.
To use ElevenLabs later, change those two functions only. The microphone needs
`https://` (or localhost).

### Accessibility
Settings (gear icon) has Larger text, a dyslexia-friendly font and High contrast.
They are remembered in the browser. Queue length is always a word plus bars.
