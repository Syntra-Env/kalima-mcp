"""Database connection manager for Kalima.

Opens the SQLite database directly (no WASM), uses WAL mode for better
concurrent read performance, and initializes tables/indexes on first connect.
"""

import os
import sqlite3
from pathlib import Path

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

    _initialize_features(conn)
    _initialize_entry_locations(conn)
    _initialize_entry_columns(conn)
    _initialize_confidence_column(conn)
    _initialize_word_search(conn)

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

def _initialize_features(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            feature_type TEXT NOT NULL,
            category TEXT,
            lookup_key TEXT NOT NULL,
            label_ar TEXT,
            label_en TEXT,
            frequency INTEGER,
            UNIQUE(feature_type, category, lookup_key)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_features_type ON features(feature_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_features_lookup ON features(feature_type, lookup_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_features_type_cat ON features(feature_type, category)")


def _initialize_entry_locations(conn: sqlite3.Connection):
    """Create entry_locations table for many-to-many entry-to-location mapping (idempotent)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entry_locations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id    TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
            surah       INTEGER NOT NULL,
            ayah_start  INTEGER,
            ayah_end    INTEGER,
            word_start  INTEGER,
            word_end    INTEGER
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_el_entry ON entry_locations(entry_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_el_verse ON entry_locations(surah, ayah_start)")
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_el_unique
        ON entry_locations(entry_id, surah, COALESCE(ayah_start, 0), COALESCE(word_start, 0))
    """)


def _initialize_entry_columns(conn: sqlite3.Connection):
    """Add feature_id and inline verification columns to entries (idempotent)."""
    cols = [
        ("feature_id", "INTEGER"),
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
    # Indexes
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_entries_feature_id ON entries(feature_id) WHERE feature_id IS NOT NULL")


def _initialize_confidence_column(conn: sqlite3.Connection):
    try:
        conn.execute("ALTER TABLE entries ADD COLUMN confidence REAL")
    except sqlite3.OperationalError:
        pass  # Column already exists


def _initialize_word_search(conn: sqlite3.Connection):
    """Ensure indexes on words and compositional tables (idempotent)."""
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_words_verse ON words(verse_surah, verse_ayah, word_index)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_words_library ON words(word_library_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_wm_library ON word_morphemes(morpheme_library_id)"
    )
