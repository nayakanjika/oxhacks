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
