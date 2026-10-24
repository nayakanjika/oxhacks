"""Q-rious: Satisfy your Q-riosity.

This file is the "control room" of the website. Each @app.route says:
"when someone visits this address, show this page".

To add a new page, copy one of the routes below, change the address and the
template name, then create the matching file in the templates/ folder.
"""

from flask import Flask, render_template

app = Flask(__name__)


@app.route("/")
def index():
    """Landing page: logo, tagline, and the guest / log in buttons."""
    return render_template("index.html")


@app.route("/login")
def login():
    """Placeholder. Real login comes later (users will be stored in Tiger Data)."""
    return render_template("login.html")


@app.route("/search")
def search():
    """Where "Continue as guest" goes. Teammates build the search bar,
    the Ask chatbot, the map and the queue pages from here."""
    return render_template("search.html")


if __name__ == "__main__":
    # Port 5001, not the default 5000, because on a Mac "AirPlay Receiver"
    # often uses port 5000 and blocks it.
    app.run(debug=True, port=5001)
