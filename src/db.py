"""Database connection manager for Kalima.

Clarified naming:
- word_types: Unique word forms (DNA).
- word_instances: Specific occurrences in the Quran (Where it appears).
- morpheme_types: Unique morpheme forms.
- word_type_morphemes: Relates a word type to its morpheme components.
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

    db_path = os.environ.get('KALIMA_DB_PATH')
    default_path = r'C:\Codex\Kalima\data\kalima.db'

    if not db_path or not Path(db_path).exists():
        db_path = default_path

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
    _initialize_entries(conn)
    _initialize_word_search(conn)

    _conn = conn
    return conn


def save_database():
    """Commit pending changes."""
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


def _initialize_entries(conn: sqlite3.Connection):
    """Create entries table with unified anchoring."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS entries (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            phase TEXT DEFAULT 'question',
            category TEXT,
            confidence REAL,
            
            -- Unified Anchoring
            anchor_type TEXT, -- 'root', 'lemma', 'morpheme', 'word_type', 'word_instance', 'surah'
            anchor_ids TEXT,  -- Single ID or 'start, end' range
            
            verification TEXT,
            notes TEXT,

            -- Verification state
            verse_queue TEXT,
            verse_current_index INTEGER DEFAULT 0,
            
            -- Activity tracking
            last_activity TEXT
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_anchor ON entries(anchor_type, anchor_ids)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_activity ON entries(last_activity)")


def _initialize_word_search(conn: sqlite3.Connection):
    """Ensure indexes on words and compositional tables (idempotent)."""
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_words_verse ON word_instances(verse_surah, verse_ayah, word_index)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_words_global ON word_instances(global_index)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_words_type ON word_instances(word_type_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_wm_type ON word_type_morphemes(morpheme_type_id)"
    )
