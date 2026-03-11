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
    _initialize_traditional(conn)
    _initialize_holonomic_indexes(conn)
    _initialize_root_structures(conn)

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

def _initialize_root_structures(conn: sqlite3.Connection):
    """Create tables for root lattice and co-occurrence (P1.1, P1.5)."""
    # Root Lattice: persistent caching of root relationships
    conn.execute("""
        CREATE TABLE IF NOT EXISTS root_lattice (
            root_a_id INTEGER NOT NULL REFERENCES features(id),
            root_b_id INTEGER NOT NULL REFERENCES features(id),
            relationship_type TEXT NOT NULL, -- 'shared_radical', 'semantic_bridge'
            strength REAL DEFAULT 0.0,
            metadata TEXT,
            PRIMARY KEY (root_a_id, root_b_id, relationship_type)
        )
    """)
    
    # Root Co-occurrence Matrix
    conn.execute("""
        CREATE TABLE IF NOT EXISTS root_cooccurrence (
            root_a_id INTEGER NOT NULL REFERENCES features(id),
            root_b_id INTEGER NOT NULL REFERENCES features(id),
            cooccurrence_count INTEGER DEFAULT 0,
            geodesic_distance REAL,
            PRIMARY KEY (root_a_id, root_b_id)
        )
    """)
    
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rl_root_a ON root_lattice(root_a_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rc_root_a ON root_cooccurrence(root_a_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rc_distance ON root_cooccurrence(geodesic_distance)")


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


def _initialize_traditional(conn: sqlite3.Connection):
    """Create table for traditional interpretations (comparison baseline)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS traditional_interpretations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            surah INTEGER NOT NULL,
            ayah INTEGER NOT NULL,
            source TEXT NOT NULL,
            interpretation TEXT NOT NULL,
            language TEXT DEFAULT 'en',
            UNIQUE(surah, ayah, source)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_trad_verse ON traditional_interpretations(surah, ayah)"
    )


def _initialize_holonomic_indexes(conn: sqlite3.Connection):
    """Ensure indexes on holonomic_entries for common query patterns."""
    # Check if holonomic_entries exists before indexing
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='holonomic_entries'"
    ).fetchone()
    if not exists:
        return
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_he_anchor ON holonomic_entries(anchor_type, anchor_ids)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_he_activity ON holonomic_entries(last_activity)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_he_category ON holonomic_entries(category)"
    )
