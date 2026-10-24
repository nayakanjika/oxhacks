import tkinter as tk
import sys
import io
import threading
import requests
import time
from datetime import datetime
import os

# ---------- GEMINI CONFIGURATION ----------
API_KEY = os.getenv("GEMINI_API_KEY")
API_KEY = "your_actual_gemini_api_key"
MODEL = "gemini-3.1-flash-lite-preview"
TIMEOUT = 60
LEVEL = {}

# ---------- PLACE DATA ----------
def get_places():
    return []


# ---------- PLACE INFORMATION ----------
def build_context():
    now = datetime.now()
    places = get_places()

    lines = [
        f"Current time: {now.strftime('%A %H:%M')}",
        "Place information:",
        "Venue details must come from the supplied place data.",
        "Live queue lengths and crowd levels are unavailable "
        "unless explicitly provided by another live data source."
    ]

    if not places:
        lines.append(
            "No place data has been supplied yet. "
            "Do not invent venue details."
        )

    for p in places:
        if p.get("open_now") is True:
            status_text = "Currently open"
        elif p.get("open_now") is False:
            status_text = "Currently closed"
        else:
            status_text = "Opening status unavailable"

        line = (
            f"{p.get('name', 'Unknown venue')} "
            f"({p.get('type', 'Unknown type')}): "
            f"{status_text}. "
            f"Address: {p.get('address', 'Unavailable')}. "
            f"Waiting time: {p.get('wait', 'unavailable')}. "
            f"Crowd level: {p.get('level', 'unavailable')}."
        )

        if p.get("rating") is not None:
            line += f" Rating: {p['rating']}/5."

        if p.get("hours"):
            line += (
                " Opening hours: "
                + "; ".join(p["hours"])
                + "."
            )

        if p.get("maps_url"):
            line += f" Map: {p['maps_url']}."

        lines.append(line)

    return "\n".join(lines)


# ---------- TKINTER INTERFACE ----------
root = tk.Tk()
root.title("Queueless Buddy")

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

root.geometry(f"{screen_width}x{screen_height}")
root.configure(bg="#1e1e2e")

chat_display = tk.Text(
    root,
    height=30,
    width=100,
    wrap="word",
    state="disabled",
    bg="#2e2e3e",
    fg="#d4d4d8",
    font=("Segoe UI", 12),
    bd=0,
    relief="flat",
    insertbackground="#d4d4d8"
)
chat_display.pack(
    pady=20,
    padx=40,
    fill="both",
    expand=True
)

chat_display.tag_configure("user", foreground="#8be9fd")
chat_display.tag_configure("gpt", foreground="#50fa7b")
chat_display.tag_configure("error", foreground="#ff5555")

input_frame = tk.Frame(root, bg="#1e1e2e")
input_frame.pack(fill="x", padx=40, pady=10)

input_box = tk.Entry(
    input_frame,
    width=100,
    font=("Segoe UI", 12),
    bg="#2e2e3e",
    fg="#d4d4d8",
    insertbackground="#d4d4d8",
    bd=0,
    relief="flat"
)
input_box.pack(
    side="left",
    fill="x",
    expand=True,
    padx=(0, 10)
)

status = tk.Label(
    root,
    text="",
    bg="#1e1e2e",
    fg="#bd93f9",
    font=("Segoe UI", 10)
)
status.pack(pady=(0, 10))


# ---------- DISPLAY OUTPUT ----------
class StdoutRedirector(io.StringIO):
    def write(self, txt):
        if not txt:
            return

        def update_display():
            chat_display.configure(state="normal")

            tag = (
                "user"
                if txt.startswith("You:")
                else "error"
                if txt.startswith("Error:")
                else "gpt"
            )

            chat_display.insert(tk.END, txt, tag)
            chat_display.configure(state="disabled")
            chat_display.see(tk.END)

        try:
            root.after(0, update_display)
        except RuntimeError:
            pass


sys.stdout = StdoutRedirector()


# ---------- GEMINI API ----------
questions = [
    "Hi! Are you looking for a cafe or a library?",
    "Would you prefer somewhere quiet, moderately busy, or lively?",
    "Do you have a preferred venue, or should I recommend one?",
    "Would you like the shortest waiting time or the closest alternative?"
]

question_index = 0
user_answers = []

messages = [
    {
        "role": "user",
        "parts": [{
            "text": (
                "You are Queueless Buddy, a friendly queue tracking assistant. "
                "Answer only questions about venues, crowds, waiting times, "
                "and opening hours. "
                "For unrelated questions, reply exactly: "
                "This is not my field of expertise. "
                "Use only the supplied place data. Never invent wait times, "
                "crowd levels, or opening hours. "
                "Recommend quieter alternatives when useful. "
                "Venue details and opening status must come from supplied data. "
                "Live waiting times and crowd levels are unavailable unless "
                "explicitly supplied. Never claim they are real time. "
                "Keep answers brief and friendly."
            )
        }]
    }
]


def call_gemini(history):
    if not API_KEY.strip() or API_KEY == "YOUR_GEMINI_API_KEY":
        return "Error: Please enter your Gemini API key in API_KEY."

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{MODEL}:generateContent"
    )

    # Retrieve current venue information
    place_context = build_context()

    prompt = (
        f"PLACE DATA:\n{place_context}\n\n"
        f"Conversation history:\n"
        + "\n".join(
            f"{m['role']}: {m['parts'][0]['text']}"
            for m in history[-8:]
        )
        + "\n\n"
        "Answer the latest user message using the supplied venue data. "
        "If the user names a venue, search for it in the supplied data. "
        "If it is not present, say it was not found in the supplied data. "
        "Do not invent details. If the user prefers the closest venue, "
        "do not claim which venue is closest unless distances are available."
    )

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 300
        }
    }

    for attempt in range(3):
        try:
            response = requests.post(
                url,
                headers={
                    "x-goog-api-key": API_KEY,
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=(10, TIMEOUT)
            )

            # Retry temporary Gemini service errors
            if response.status_code in (429, 500, 502, 503, 504):
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                    continue

                return (
                    f"Error: Gemini HTTP {response.status_code}: "
                    f"{response.text[:300]}. "
                    "Retries exhausted. Please try again later."
                )

            if response.status_code != 200:
                return (
                    f"Error: Gemini HTTP {response.status_code}: "
                    f"{response.text[:300]}"
                )

            data = response.json()
            candidates = data.get("candidates", [])

            if candidates:
                parts = (
                    candidates[0]
                    .get("content", {})
                    .get("parts", [])
                )

                reply = "".join(
                    part.get("text", "")
                    for part in parts
                ).strip()

                if reply:
                    return reply

            return "Sorry, Gemini returned no response. Please try again."

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError
        ) as e:
            if attempt < 2:
                time.sleep(2 ** (attempt + 1))
                continue

            return (
                f"Error: {type(e).__name__}: {e}. "
                "Please try again."
            )

        except Exception as e:
            return f"Error: {type(e).__name__}: {e}"

    return "Sorry, I could not connect to Gemini."


# ---------- SEND INPUT ----------
def send_input(event=None):
    global question_index, user_answers

    user_input = input_box.get().strip()

    if not user_input:
        return

    input_box.delete(0, tk.END)
    print(f"You: {user_input}\n")

    if user_input.lower() in [
        "bye",
        "goodbye",
        "thanks bye",
        "thank you"
    ]:
        print(
            "Queueless Buddy: Thanks for chatting! "
            "Hope you find a quiet spot!\n"
        )
        return

    if question_index < len(questions):
        user_answers.append(user_input)
        question_index += 1

        if question_index < len(questions):
            print(
                f"Queueless Buddy: "
                f"{questions[question_index]}\n"
            )
            return

    messages.append({
        "role": "user",
        "parts": [{
            "text": (
                f"User preferences and latest message: {user_answers}\n"
                f"Latest message: {user_input}"
            )
        }]
    })

    status.config(text="Thinking...")
    input_box.config(state="disabled")

    def worker():
        reply = call_gemini(messages)

        def finish():
            status.config(text="")
            input_box.config(state="normal")
            input_box.focus()

            print(f"Queueless Buddy: {reply}\n")

            messages.append({
                "role": "model",
                "parts": [{"text": reply}]
            })

            del messages[1:-10]

        try:
            root.after(0, finish)
        except RuntimeError:
            pass

    threading.Thread(target=worker, daemon=True).start()


input_box.bind("<Return>", send_input)

print(
    "Queueless Buddy: Hi! Ask me about nearby cafes, "
    "libraries, opening hours, and available venue information.\n"
)


# ---------- CHECK AVAILABLE GEMINI MODELS ----------
def check_models():
    try:
        r = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            headers={"x-goog-api-key": API_KEY},
            timeout=20
        )

        if r.status_code != 200:
            msg = (
                f"Error: model list HTTP {r.status_code}: "
                f"{r.text[:300]}\n"
            )
        else:
            names = [
                m["name"].replace("models/", "")
                for m in r.json().get("models", [])
                if "generateContent"
                in m.get("supportedGenerationMethods", [])
            ]

            msg = (
                "Models your key can use: "
                + ", ".join(names[:15])
                + "\n"
            )

            if MODEL not in names:
                msg += (
                    f"Error: MODEL {MODEL} is not in that list. "
                    "Change MODEL.\n"
                )

    except Exception as e:
        msg = f"Error: {type(e).__name__}: {e}\n"

    root.after(0, lambda: print(msg))


threading.Thread(target=check_models, daemon=True).start()

input_box.focus()
root.mainloop()
