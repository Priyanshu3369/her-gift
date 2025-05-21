from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import date, datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps
import os
from dotenv import load_dotenv
load_dotenv()  # loads variables from .env into os.environ

app = Flask(__name__)
DB_NAME = "notes.db"
app.secret_key = os.getenv('SECRET_KEY')

if not app.secret_key:
    raise RuntimeError("SECRET_KEY environment variable not set!")

LOVE_NOTES_PASSWORD = os.getenv('LOVE_NOTES_PASSWORD')
if not LOVE_NOTES_PASSWORD:
    raise RuntimeError("LOVE_NOTES_PASSWORD environment variable not set!")



# ---------------------- DB Initialization ----------------------
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Always create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')

        # Always create notes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                tag TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Reminders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                remind_at TEXT NOT NULL,
                seen INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Love Notes table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS love_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Moods table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS moods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                mood TEXT NOT NULL,
                date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Planner table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS planner (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                due_date TEXT NOT NULL,
                due_time TEXT,
                done INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Diary entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diary_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                entry_date TEXT NOT NULL,
                content TEXT NOT NULL,
                UNIQUE(user_id, entry_date),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        # Diary passwords table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS diary_passwords (
                user_id INTEGER PRIMARY KEY,
                password TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        ''')

        conn.commit()


# Ensure DB is initialized only once
init_db()


# ---------------------- Login Required Decorator ----------------------
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("You must be logged in to view that page.")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ---------------------- Register Route ----------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("name")  # Make sure HTML form uses name="name"
        password_raw = request.form.get("password")

        if not username or not password_raw:
            flash("Please fill in all required fields.")
            return render_template("register.html")

        hashed_password = generate_password_hash(password_raw)

        try:
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
                conn.commit()
            flash("Registration successful! Please log in.")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Username already exists. Try another.")
            return render_template("register.html")

    return render_template("register.html")


# ---------------------- Login Route ----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if not username or not password:
            flash("Please fill in all required fields.")
            return render_template("login.html")

        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, password FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()

        if user and check_password_hash(user[1], password):
            session.clear()  # Clear any existing session first
            session["user_id"] = user[0]
            session["username"] = username  # Optional: store username
            flash("Welcome back!")
            return redirect(url_for("home"))
        else:
            flash("Invalid credentials.")

    return render_template("login.html")


# ---------------------- Logout Route ----------------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for("login"))


# ---------------------- Home ----------------------
@app.route("/")
@login_required
def home():
    return render_template("home.html")


# ---------------------- Notes ----------------------
@app.route("/notes", methods=["GET", "POST"])
@login_required
def notes():
    user_id = session["user_id"]
    if request.method == "POST":
        content = request.form["content"]
        tag = request.form["tag"]
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO notes (content, tag, user_id) VALUES (?, ?, ?)", (content, tag, user_id))
            conn.commit()
        return redirect(url_for("notes"))

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM notes WHERE user_id = ? ORDER BY id DESC", (user_id,))
        all_notes = cursor.fetchall()

    return render_template("notes.html", notes=all_notes)


@app.route("/notes/delete/<int:note_id>")
@login_required
def delete_note(note_id):
    user_id = session["user_id"]
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Ensure the note belongs to the logged-in user
        cursor.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id))
        conn.commit()
    return redirect(url_for("notes"))


@app.route("/notes/edit/<int:note_id>", methods=["GET", "POST"])
@login_required
def edit_note(note_id):
    user_id = session["user_id"]
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Fetch the note only if it belongs to the current user
        cursor.execute("SELECT * FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id))
        note = cursor.fetchone()

    if not note:
        flash("Note not found or access denied.")
        return redirect(url_for("notes"))

    if request.method == "POST":
        updated_content = request.form["content"]
        updated_tag = request.form["tag"]
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE notes SET content = ?, tag = ? WHERE id = ? AND user_id = ?",
                           (updated_content, updated_tag, note_id, user_id))
            conn.commit()
        return redirect(url_for("notes"))

    return render_template("edit_note.html", note=note)



@app.route("/reminders", methods=["GET", "POST"])
@login_required
def reminders():
    user_id = session["user_id"]

    if request.method == "POST":
        title = request.form["title"]
        remind_at = request.form["remind_at"].replace("T", " ")
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO reminders (title, remind_at, user_id) VALUES (?, ?, ?)", (title, remind_at, user_id))
            conn.commit()
        return redirect(url_for("reminders"))

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reminders WHERE user_id = ? ORDER BY remind_at ASC", (user_id,))
        reminders = cursor.fetchall()

    return render_template("reminders.html", reminders=reminders)


@app.route("/reminders/edit/<int:reminder_id>", methods=["GET", "POST"])
@login_required
def edit_reminder(reminder_id):
    user_id = session["user_id"]
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reminders WHERE id = ? AND user_id = ?", (reminder_id, user_id))
        reminder = cursor.fetchone()

    if not reminder:
        flash("Reminder not found or access denied.")
        return redirect(url_for("reminders"))

    if request.method == "POST":
        title = request.form["title"]
        remind_at = request.form["remind_at"]
        with sqlite3.connect(DB_NAME) as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE reminders SET title = ?, remind_at = ?, seen = 0 WHERE id = ? AND user_id = ?",
                           (title, remind_at, reminder_id, user_id))
            conn.commit()
        return redirect(url_for("reminders"))

    return render_template("edit_reminder.html", reminder=reminder)


@app.route("/reminders/delete/<int:reminder_id>")
@login_required
def delete_reminder(reminder_id):
    user_id = session["user_id"]
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reminders WHERE id = ? AND user_id = ?", (reminder_id, user_id))
        conn.commit()
    return redirect(url_for("reminders"))


@app.route("/check_reminders")
@login_required
def check_reminders():
    user_id = session["user_id"]
    now = datetime.now().replace(second=0, microsecond=0)

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, remind_at FROM reminders WHERE seen = 0 AND user_id = ?", (user_id,))
        reminders = cursor.fetchall()

        to_show = []
        for r in reminders:
            db_time = datetime.strptime(r[2], "%Y-%m-%d %H:%M")
            if db_time <= now:
                to_show.append(r)
                cursor.execute("UPDATE reminders SET seen = 1 WHERE id = ?", (r[0],))

        conn.commit()

    return {"reminders": to_show}



@app.route("/love-notes/login", methods=["GET", "POST"])
@login_required
def love_notes_login():
    if session.get("love_notes_unlocked"):
        return redirect(url_for("love_notes"))

    if request.method == "POST":
        password = request.form["password"]
        if password == LOVE_NOTES_PASSWORD:
            session["love_notes_unlocked"] = True
            return redirect(url_for("love_notes"))
        else:
            flash("Incorrect password. Try again.")
    return render_template("love_notes_login.html")



@app.route("/love-notes/logout")
@login_required
def love_notes_logout():
    session.pop("love_notes_unlocked", None)
    flash("Love Notes locked again 🔐")
    return redirect(url_for("love_notes_login"))



@app.route("/love-notes")
@login_required
def love_notes():
    if not session.get("love_notes_unlocked"):
        return redirect(url_for("love_notes_login"))
    return render_template("love_notes.html")





@app.route("/mood", methods=["GET", "POST"])
@login_required
def mood():
    user_id = session["user_id"]
    today = datetime.now().strftime("%Y-%m-%d")

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        if request.method == "POST":
            cursor.execute("SELECT id FROM moods WHERE user_id = ? AND date = ?", (user_id, today))
            if cursor.fetchone():
                flash("Aaj ka mood already save ho chuka hai 😇")
            else:
                mood = request.form["mood"]
                cursor.execute("INSERT INTO moods (mood, date, user_id) VALUES (?, ?, ?)", (mood, today, user_id))
                conn.commit()
                flash("Mood saved! ❤️")

        # Get last 7 days
        week_dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]
        cursor.execute("SELECT mood, date FROM moods WHERE user_id = ? AND date >= ?", (user_id, week_dates[0]))
        fetched = cursor.fetchall()

        # Map to dictionary for quick lookup
        mood_lookup = {date: mood for mood, date in fetched}

        # Fill mood_data with all 7 days
        mood_data = [{"date": d, "mood": mood_lookup.get(d)} for d in week_dates]

    latest_mood = next((entry["mood"] for entry in reversed(mood_data) if entry["mood"]), None)

    affirmations = {
        "😊": "Keep smiling, sunshine ☀️",
        "😐": "It’s okay to feel neutral. Take a deep breath 🌿",
        "😔": "You're stronger than you feel right now 💪",
        "😡": "Take a pause. You deserve peace 🕊️",
        "😍": "You're glowing with love 💖"
    }

    message = affirmations.get(latest_mood, "")
    already_submitted = any(m["date"] == today and m["mood"] for m in mood_data)

    return render_template("mood.html", moods=mood_data, affirmation=message, already_submitted=already_submitted)




@app.route("/planner", methods=["GET", "POST"])
@login_required
def planner():
    user_id = session["user_id"]

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        if request.method == "POST":
            if "delete" in request.form:
                task_id = request.form["delete"]
                cursor.execute("DELETE FROM planner WHERE id = ? AND user_id = ?", (task_id, user_id))
            elif "done" in request.form:
                task_id = request.form["done"]
                cursor.execute("UPDATE planner SET done = 1 WHERE id = ? AND user_id = ?", (task_id, user_id))
            else:
                title = request.form["title"]
                description = request.form.get("description")
                due_date = request.form["due_date"]
                due_time = request.form.get("due_time")
                cursor.execute(
                    "INSERT INTO planner (title, description, due_date, due_time, user_id) VALUES (?, ?, ?, ?, ?)",
                    (title, description, due_date, due_time, user_id)
                )
            conn.commit()
            return redirect(url_for("planner"))

        filter_date = request.args.get("date")
        if filter_date:
            cursor.execute(
                "SELECT * FROM planner WHERE user_id = ? AND due_date = ? ORDER BY due_date ASC, due_time ASC",
                (user_id, filter_date)
            )
            selected_date = filter_date
        else:
            today = datetime.now().strftime("%Y-%m-%d")
            cursor.execute(
                "SELECT * FROM planner WHERE user_id = ? AND due_date >= ? ORDER BY due_date ASC, due_time ASC",
                (user_id, today)
            )
            selected_date = ""

        tasks = cursor.fetchall()

        today_obj = datetime.today()
        week_dates = [(today_obj + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
        summary = []
        for date in week_dates:
            cursor.execute(
                "SELECT COUNT(*), SUM(done) FROM planner WHERE user_id = ? AND due_date = ?",
                (user_id, date)
            )
            total, done = cursor.fetchone()
            total = total or 0
            done = done or 0
            summary.append({
                "date": date,
                "total": total,
                "done": done,
                "pending": total - done
            })

    return render_template("planner.html", tasks=tasks, selected_date=selected_date, summary=summary)


@app.route("/planner/events")
@login_required
def planner_events():
    user_id = session["user_id"]

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT title, due_date, due_time FROM planner WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        events = []
        for title, date, time in rows:
            dt = date
            if time:
                dt += f"T{time}"
            events.append({
                "title": title,
                "start": dt
            })
    return {"events": events}



########################### Diary Routes #######################################
@app.route("/diary/lock", methods=["GET", "POST"])
@login_required
def diary_lock():
    user_id = session["user_id"]
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        if request.method == "POST":
            raw_pass = request.form["password"]
            hashed_pass = generate_password_hash(raw_pass)
            cursor.execute("REPLACE INTO diary_passwords (user_id, password) VALUES (?, ?)", (user_id, hashed_pass))
            conn.commit()
            flash("Diary password set successfully!")
            return redirect(url_for("diary_unlock"))

    return render_template("diary_lock.html")


@app.route("/diary/unlock", methods=["GET", "POST"])
@login_required
def diary_unlock():
    user_id = session["user_id"]
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM diary_passwords WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()

        if row is None:
            # No password set yet — ask user to set one
            if request.method == "POST":
                new_password = request.form["new_password"]
                if new_password:
                    hashed_pass = generate_password_hash(new_password)
                    cursor.execute("INSERT INTO diary_passwords (user_id, password) VALUES (?, ?)", (user_id, hashed_pass))
                    conn.commit()
                    session["diary_unlocked"] = True
                    flash("Diary password set successfully!", "info")
                    return redirect(url_for("diary"))
            return render_template("diary_set_password.html")

        else:
            # Password is already set — ask to enter it
            if request.method == "POST":
                input_password = request.form["password"]
                if check_password_hash(row[0], input_password):  # ✅ Corrected line
                    session["diary_unlocked"] = True
                    return redirect(url_for("diary"))
                else:
                    flash("Incorrect diary password. Please try again.", "error")
            return render_template("diary_unlock.html")




@app.route("/diary", methods=["GET", "POST"])
@login_required
def diary():
    if not session.get("diary_unlocked"):
        return redirect(url_for("diary_unlock"))

    user_id = session["user_id"]
    today = datetime.now().strftime("%Y-%m-%d")

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        if request.method == "POST":
            content = request.form["content"]
            cursor.execute(
                "REPLACE INTO diary_entries (user_id, entry_date, content) VALUES (?, ?, ?)",
                (user_id, today, content)
            )
            conn.commit()
            flash("Today's diary entry saved!")

        # Load today's entry if it exists (for pre-fill or editing)
        cursor.execute(
            "SELECT content FROM diary_entries WHERE user_id = ? AND entry_date = ?",
            (user_id, today)
        )
        result = cursor.fetchone()
        today_entry = result[0] if result else ""

    return render_template("diary.html", today=today, content=today_entry, diary_unlocked=True)


@app.route("/diary/entries")
@login_required
def view_entries():
    if not session.get("diary_unlocked"):
        return redirect(url_for("diary_unlock"))

    user_id = session["user_id"]
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT entry_date, content FROM diary_entries WHERE user_id = ? ORDER BY entry_date DESC",
            (user_id,)
        )
        entries = cursor.fetchall()

    formatted_entries = [
        {"entry_date": d, "content": c} for d, c in entries
    ]
    return render_template("diary_view.html", entries=formatted_entries)


@app.route("/diary/view/<date>")
@login_required
def view_diary_entry(date):
    if not session.get("diary_unlocked"):
        return redirect(url_for("diary_unlock"))

    user_id = session["user_id"]
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT content FROM diary_entries WHERE user_id = ? AND entry_date = ?",
            (user_id, date)
        )
        result = cursor.fetchone()

    if result:
        content = result[0]
    else:
        flash("No diary entry found for that date.")
        return redirect(url_for("view_entries"))

    return render_template("diary_view.html", date=date, content=content)



if __name__ == "__main__":
    app.run(debug=True)
