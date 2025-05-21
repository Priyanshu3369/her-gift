import sqlite3

DB_NAME = "notes.db"  # Use the correct database name

def migrate_moods_table():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Check if 'moods' table exists and has a 'timestamp' column
        cursor.execute("PRAGMA table_info(moods);")
        columns = [col[1] for col in cursor.fetchall()]
        
        if "timestamp" in columns:
            print("Migrating 'moods' table...")

            # Rename old table
            cursor.execute("ALTER TABLE moods RENAME TO old_moods;")

            # Create new table with correct schema
            cursor.execute('''
                CREATE TABLE moods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mood TEXT NOT NULL,
                    date TEXT NOT NULL
                )
            ''')

            # Copy data from old table to new table
            cursor.execute('''
                INSERT INTO moods (id, mood, date)
                SELECT id, mood, timestamp FROM old_moods;
            ''')

            # Drop the old table
            cursor.execute("DROP TABLE old_moods;")

            conn.commit()
            print("Migration complete.")
        else:
            print("No migration needed. 'moods' table is already up to date.")

migrate_moods_table()
