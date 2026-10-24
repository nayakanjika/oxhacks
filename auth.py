"""Q-rious accounts: sign up, log in, using Muhammed's `users` table in Tiger Data.

Passwords are never stored as plain text. They are scrambled (hashed) with
Werkzeug before they go into the `password_hash` column.

Everything here fails politely: if the database or the column isn't ready,
the functions return a friendly message instead of crashing the site.
"""

from werkzeug.security import check_password_hash, generate_password_hash

import places_data

NOT_READY = "Accounts aren't switched on yet. You can carry on as a guest."


def _clean_email(email):
    return str(email or "").strip().lower()


def _message_for(error):
    text = str(error).lower()
    if "password_hash" in text:
        return NOT_READY
    return "Something went wrong talking to the database. Please try again, or carry on as a guest."


def sign_up(name, email, password):
    """Returns (user_dict, None) or (None, friendly_error)."""
    name = str(name or "").strip()[:60]
    email = _clean_email(email)
    password = str(password or "")
    if not name:
        return None, "Please enter your name."
    if "@" not in email or "." not in email.split("@")[-1]:
        return None, "Please enter a valid email address."
    if len(password) < 8:
        return None, "Your password needs at least 8 characters."
    if not places_data.db_configured():
        return None, NOT_READY

    pw_hash = generate_password_hash(password, method="pbkdf2:sha256")
    conn = None
    try:
        conn = places_data._connect()
        with conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE lower(email) = %s", (email,))
            if cur.fetchone():
                return None, "There is already an account with that email. Try logging in."
            try:
                cur.execute(
                    "INSERT INTO users (email, name, password_hash, created_at) "
                    "VALUES (%s, %s, %s, now()) RETURNING id",
                    (email, name, pw_hash))
            except Exception as e:
                if "null value in column \"id\"" not in str(e):
                    raise
                conn.rollback()
                cur.execute(
                    "INSERT INTO users (id, email, name, password_hash, created_at) "
                    "SELECT coalesce(max(id), 0) + 1, %s, %s, %s, now() FROM users RETURNING id",
                    (email, name, pw_hash))
            uid = cur.fetchone()[0]
        return {"id": str(uid), "name": name, "email": email}, None
    except Exception as e:  # noqa: BLE001 - we want to show a friendly message
        return None, _message_for(e)
    finally:
        if conn is not None:
            conn.close()


def log_in(email, password):
    """Returns (user_dict, None) or (None, friendly_error)."""
    email = _clean_email(email)
    password = str(password or "")
    if not email or not password:
        return None, "Please enter your email and password."
    if not places_data.db_configured():
        return None, NOT_READY

    conn = None
    try:
        conn = places_data._connect()
        with conn, conn.cursor() as cur:
            cur.execute("SELECT id, name, email, password_hash FROM users WHERE lower(email) = %s", (email,))
            row = cur.fetchone()
        if not row or not row[3] or not check_password_hash(row[3], password):
            return None, "That email and password don't match."
        return {"id": str(row[0]), "name": row[1] or "there", "email": row[2]}, None
    except Exception as e:  # noqa: BLE001
        return None, _message_for(e)
    finally:
        if conn is not None:
            conn.close()
