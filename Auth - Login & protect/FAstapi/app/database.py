import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "tasks.db"


def get_db_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            title TEXT,
            done BOOLEAN
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM tasks")
    if cursor.fetchone()[0] == 0:
        sample_tasks = [
            (1, "Study FastAPI", False),
            (2, "Read book", True),
            (3, "Go to gym", False),
        ]
        cursor.executemany("INSERT INTO tasks (id, title, done) VALUES (?, ?, ?)", sample_tasks)
    conn.commit()
    conn.close()
