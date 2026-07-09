"""SQLite tabanlı basit konuşma hafızası."""
import sqlite3
from pathlib import Path

DB_PATH = Path("memory.db")


def init_db() -> None:
    """Uygulama başlarken bir kez çağrılır, tabloları oluşturur."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id)
        )
    """)
    conn.commit()
    conn.close()


def ensure_session(session_id: str) -> None:
    """Session yoksa oluşturur (varsa dokunmaz)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO sessions (id) VALUES (?)", (session_id,)
    )
    conn.commit()
    conn.close()


def save_message(session_id: str, role: str, content: str) -> None:
    ensure_session(session_id)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
        (session_id, role, content),
    )
    conn.commit()
    conn.close()


def get_recent_history(session_id: str, limit: int = 10) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        """
        SELECT role, content FROM messages
        WHERE session_id = ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (session_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    # DESC ile çektik, LLM'e kronolojik sırayla göndermek için ters çeviriyoruz
    return [{"role": role, "content": content} for role, content in reversed(rows)]