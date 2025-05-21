import sqlite3

conn = sqlite3.connect("notes.db")  # Replace with your actual DB filename
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS diary_passwords (
    user_id INTEGER PRIMARY KEY,
    password TEXT NOT NULL
)
""")

conn.commit()
conn.close()
