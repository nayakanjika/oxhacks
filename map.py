
import os
from flask import Flask, render_template
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

app = Flask(__name__)

@app.route("/")
def index():
    return render_template(
        "map.html",
        api_key=os.getenv("GOOGLE_MAPS_API_KEY", "")
    )

if __name__ == "__main__":
    app.run(debug=True)
