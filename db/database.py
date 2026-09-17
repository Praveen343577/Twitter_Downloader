import sqlite3
from datetime import datetime
from config import DB_FILE

def init_db():
    """Initializes the SQLite database and creates the downloads table if it does not exist."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                account_name TEXT,
                username TEXT,
                description TEXT,
                status TEXT,
                download_date DATETIME
            )
        ''')
        conn.commit()

def is_downloaded(url: str) -> bool:
    """Checks if a sanitized URL already exists in the database."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM downloads WHERE url = ? AND status = 'SUCCESS'", (url,))
        return cursor.fetchone() is not None

def insert_record(url: str, account_name: str | None, username: str | None, description: str | None, status: str):
    """Inserts or updates a download record upon sequence completion or explicit failure."""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        now_local = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
        cursor.execute('''
            INSERT OR REPLACE INTO downloads (url, account_name, username, description, status, download_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (url, account_name, username, description, status, now_local))
        conn.commit()
