"""backend/database.py"""
import sqlite3, os


def get_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = get_db(db_path)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL, avatar TEXT DEFAULT '',
        theme TEXT DEFAULT 'light', role TEXT DEFAULT 'individual',
        created_at TEXT DEFAULT (datetime('now')))""")

    c.execute("""CREATE TABLE IF NOT EXISTS chat_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL, title TEXT NOT NULL DEFAULT 'New Research',
        is_pinned INTEGER DEFAULT 0, is_archived INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER NOT NULL, role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (session_id) REFERENCES chat_sessions(id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL, title TEXT NOT NULL,
        doc_type TEXT NOT NULL, content TEXT NOT NULL,
        status TEXT DEFAULT 'generated',
        is_pinned INTEGER DEFAULT 0, is_archived INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        updated_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id))""")

    c.execute("""CREATE TABLE IF NOT EXISTS doc_analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL, title TEXT NOT NULL,
        question TEXT NOT NULL, answer TEXT NOT NULL,
        doc_snippet TEXT DEFAULT '',
        is_pinned INTEGER DEFAULT 0, is_archived INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id))""")

    conn.commit()
    conn.close()


def migrate_db(db_path: str):
    conn = get_db(db_path)
    c = conn.cursor()
    safe_cols = [
        ("users",         "role",         "TEXT DEFAULT 'individual'"),
        ("chat_sessions", "is_pinned",    "INTEGER DEFAULT 0"),
        ("chat_sessions", "is_archived",  "INTEGER DEFAULT 0"),
        ("documents",     "is_pinned",    "INTEGER DEFAULT 0"),
        ("documents",     "is_archived",  "INTEGER DEFAULT 0"),
        ("documents",     "status",       "TEXT DEFAULT 'generated'"),
        ("documents",     "updated_at",   "TEXT DEFAULT (datetime('now'))"),
        ("doc_analyses",  "is_pinned",    "INTEGER DEFAULT 0"),
        ("doc_analyses",  "is_archived",  "INTEGER DEFAULT 0"),
    ]
    for table, col, defn in safe_cols:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")
        except Exception:
            pass
    c.execute("""CREATE TABLE IF NOT EXISTS doc_analyses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL, title TEXT NOT NULL,
        question TEXT NOT NULL, answer TEXT NOT NULL,
        doc_snippet TEXT DEFAULT '',
        is_pinned INTEGER DEFAULT 0, is_archived INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id))""")
    conn.commit()
    conn.close()
