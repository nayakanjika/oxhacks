"""Q-rious: Satisfy your Q-riosity.

This file is the "control room" of the website. Each @app.route says:
"when someone visits this address, show this page".

To add a new page, copy one of the routes below, change the address and the
template name, then create the matching file in the templates/ folder.
"""

import os

from flask import Flask, redirect, render_template, request, session, url_for

import auth

from api import api  # the /api routes (places, chat, report): see api.py
from voice import voice  # ElevenLabs voice routes: see voice.py

app = Flask(__name__)
# Signs the login cookie. Put SECRET_KEY=any-long-random-text in .env (on every server).
app.secret_key = os.environ.get("SECRET_KEY") or "qrious-dev-secret-change-me"
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
app.register_blueprint(api)
app.register_blueprint(voice)


@app.route("/")
def index():
    """Landing page: logo, tagline, and the guest / log in buttons."""
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log in or create an account (users live in Tiger Data, see auth.py)."""
    mode = "signup" if request.values.get("mode") == "signup" else "login"
    error, email, name = None, "", ""
    if request.method == "POST":
        email = request.form.get("email", "")
        name = request.form.get("name", "")
        if mode == "signup":
            user, error = auth.sign_up(name, email, request.form.get("password"))
        else:
            user, error = auth.log_in(email, request.form.get("password"))
        if user:
            session["user"] = user
            return redirect(url_for("search"))
    return render_template("login.html", mode=mode, error=error, email=email, name=name)


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("index"))


@app.route("/search")
def search():
    """Where "Continue as guest" goes. Teammates build the search bar,
    the Ask chatbot, the map and the queue pages from here."""
    # The Google Maps key lives in .env (GOOGLE_MAPS_API_KEY). Empty = sample map.
    return render_template("search.html", maps_key=os.environ.get("GOOGLE_MAPS_API_KEY", ""))


if __name__ == "__main__":
    # Port 5001, not the default 5000, because on a Mac "AirPlay Receiver"
    # often uses port 5000 and blocks it.
    app.run(debug=True, port=5001)
