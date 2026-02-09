"""Database connection manager for Kalima.

Opens the SQLite database directly (no WASM), uses WAL mode for better
concurrent read performance, and initializes tables/indexes on first connect.
"""

import os
import sqlite3
from pathlib import Path

from .utils.arabic import normalize_arabic

_conn: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    """Get or create the singleton database connection."""
    global _conn
    if _conn is not None:
        return _conn

    db_path = os.environ.get(
        'KALIMA_DB_PATH',
        str(Path(__file__).resolve().parent.parent / 'data' / 'kalima.db')
    )

    if not Path(db_path).exists():
        raise FileNotFoundError(
            f"Database not found at {db_path}. "
            f"Set KALIMA_DB_PATH environment variable to the correct path."
        )

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    _initialize_ref_features(conn)
    _initialize_scope_columns(conn)
    _initialize_confidence_column(conn)
    _initialize_search_index(conn)

    _conn = conn
    return conn


def save_database():
    """Commit pending changes. With native sqlite3 this is just a commit."""
    if _conn:
        _conn.commit()


def close_database():
    """Close the database connection."""
    global _conn
    if _conn:
        _conn.close()
        _conn = None


# --- Initialization functions ---

def _initialize_ref_features(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ref_features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feature_type TEXT NOT NULL,
            category TEXT,
            lookup_key TEXT NOT NULL,
            label_ar TEXT,
            label_en TEXT,
            buckwalter TEXT,
            frequency INTEGER,
            extra TEXT,
            UNIQUE(feature_type, category, lookup_key)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ref_features_type ON ref_features(feature_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ref_features_lookup ON ref_features(feature_type, lookup_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ref_features_type_cat ON ref_features(feature_type, category)")



def _initialize_scope_columns(conn: sqlite3.Connection):
    """Add scope and inline verification columns to entries (idempotent)."""
    cols = [
        ("scope_type", "TEXT"),
        ("scope_value", "TEXT"),
        ("verse_total", "INTEGER"),
        ("verse_verified", "INTEGER DEFAULT 0"),
        ("verse_supports", "INTEGER DEFAULT 0"),
        ("verse_contradicts", "INTEGER DEFAULT 0"),
        ("verse_unclear", "INTEGER DEFAULT 0"),
        ("verse_current_index", "INTEGER DEFAULT 0"),
        ("verse_queue", "TEXT"),
        ("verification_started_at", "TEXT"),
        ("verification_updated_at", "TEXT"),
    ]
    for col_name, col_type in cols:
        try:
            conn.execute(f"ALTER TABLE entries ADD COLUMN {col_name} {col_type}")
        except sqlite3.OperationalError:
            pass  # Column already exists



def _initialize_confidence_column(conn: sqlite3.Connection):
    try:
        conn.execute("ALTER TABLE entries ADD COLUMN confidence REAL")
    except sqlite3.OperationalError:
        pass  # Column already exists


def _initialize_search_index(conn: sqlite3.Connection):
    # Add normalized_text column if it doesn't exist
    try:
        conn.execute("ALTER TABLE verse_texts ADD COLUMN normalized_text TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Check if normalized texts need to be populated
    row = conn.execute(
        "SELECT COUNT(*) FROM verse_texts WHERE normalized_text IS NULL"
    ).fetchone()
    null_count = row[0]

    if null_count > 0:
        rows = conn.execute(
            "SELECT surah_number, ayah_number, text FROM verse_texts"
        ).fetchall()

        for r in rows:
            normalized = normalize_arabic(r[2])
            conn.execute(
                "UPDATE verse_texts SET normalized_text = ? WHERE surah_number = ? AND ayah_number = ?",
                (normalized, r[0], r[1])
            )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_verse_texts_normalized ON verse_texts(normalized_text)"
        )

        conn.commit()
