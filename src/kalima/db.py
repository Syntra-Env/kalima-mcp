"""Database connection manager for Kalima.

Opens the SQLite database directly (no WASM), uses WAL mode for better
concurrent read performance, and initializes views/tables/indexes on first connect.
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
        str(Path(__file__).resolve().parent.parent.parent / 'data' / 'database' / 'kalima.db')
    )

    if not Path(db_path).exists():
        # Also check quran.db in project root
        alt_path = str(Path(__file__).resolve().parent.parent.parent / 'quran.db')
        if Path(alt_path).exists():
            db_path = alt_path
        else:
            raise FileNotFoundError(
                f"Database not found at {db_path}. "
                f"Set KALIMA_DB_PATH environment variable to the correct path."
            )

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    _initialize_verse_claims_view(conn)
    _initialize_pattern_linguistic_features(conn)
    _initialize_workflow_tables(conn)
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


# --- Graph cache invalidation hook ---

_graph_invalidation_callback = None


def set_graph_invalidation_callback(callback):
    """Register a callback to invalidate the graph cache on writes."""
    global _graph_invalidation_callback
    _graph_invalidation_callback = callback


def invalidate_graph_cache():
    """Call the registered graph cache invalidation callback."""
    if _graph_invalidation_callback:
        _graph_invalidation_callback()


# --- Initialization functions ---

def _initialize_verse_claims_view(conn: sqlite3.Connection):
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_claim_evidence_verse
        ON claim_evidence(surah, ayah)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_verse_evidence_verse
        ON verse_evidence(verse_surah, verse_ayah)
    """)

    conn.execute("DROP VIEW IF EXISTS verse_claims")

    conn.execute("""
        CREATE VIEW verse_claims AS
        SELECT
            surah,
            ayah,
            claim_id,
            'claim_evidence' as evidence_type,
            notes,
            NULL as verification,
            created_at
        FROM claim_evidence
        UNION ALL
        SELECT
            verse_surah as surah,
            verse_ayah as ayah,
            claim_id,
            'verse_evidence' as evidence_type,
            notes,
            verification,
            verified_at as created_at
        FROM verse_evidence
    """)


def _initialize_pattern_linguistic_features(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pattern_linguistic_features (
            id TEXT PRIMARY KEY,
            pattern_id TEXT,
            feature_type TEXT NOT NULL,
            feature_value TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (pattern_id) REFERENCES patterns(id) ON DELETE CASCADE
        )
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_pattern_ling_features_pattern
        ON pattern_linguistic_features(pattern_id)
    """)

    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_pattern_ling_features_type_value
        ON pattern_linguistic_features(feature_type, feature_value)
    """)


def _initialize_workflow_tables(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS workflow_sessions (
            session_id TEXT PRIMARY KEY,
            claim_id TEXT NOT NULL,
            workflow_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            current_index INTEGER NOT NULL,
            total_verses INTEGER NOT NULL,
            status TEXT NOT NULL,
            linguistic_features TEXT,
            surah INTEGER,
            verses_json TEXT NOT NULL,
            FOREIGN KEY (claim_id) REFERENCES claims(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS verse_evidence (
            id TEXT PRIMARY KEY,
            claim_id TEXT NOT NULL,
            verse_surah INTEGER NOT NULL,
            verse_ayah INTEGER NOT NULL,
            verification TEXT NOT NULL,
            notes TEXT,
            verified_at TEXT NOT NULL,
            FOREIGN KEY (claim_id) REFERENCES claims(id)
        )
    """)


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
