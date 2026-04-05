"""Database connection manager for Scholar.

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

HF_REPO_ID = "Syntra-Env/scholar-db"
HF_FILENAME = "kalima.db"
DEFAULT_DB_PATH = Path.home() / ".scholar" / "data" / "kalima.db"


def _download_from_hf() -> str:
    """Download scholar.db from HuggingFace and save locally."""
    try:
        from huggingface_hub import hf_hub_download
        import shutil
        
        print(f"Downloading database from HuggingFace ({HF_REPO_ID})...")
        
        # Download to cache
        cached_path = hf_hub_download(
            repo_id=HF_REPO_ID,
            filename=HF_FILENAME,
            repo_type="dataset"
        )
        
        # Save to default location
        DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(cached_path, DEFAULT_DB_PATH)
        print(f"Database saved to: {DEFAULT_DB_PATH}")
        
        return str(DEFAULT_DB_PATH)
    except Exception as e:
        print(f"Failed to download from HuggingFace: {e}")
        return None


def get_connection() -> sqlite3.Connection:
    """Get or create the singleton database connection."""
    global _conn
    if _conn is not None:
        return _conn

    # Priority: env var > default path > relative path > HF download
    db_path = os.environ.get('SCHOLAR_DB_PATH')

    if db_path and not Path(db_path).exists():
        # Env var set but path doesn't exist - try to create parent dirs
        # and proceed (will create new DB at that path)
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    elif not db_path:
        # Try default path
        if DEFAULT_DB_PATH.exists():
            db_path = str(DEFAULT_DB_PATH)
        else:
            # Try current directory relative path
            alt_path = Path("data/scholar.db")
            if alt_path.exists():
                db_path = str(alt_path.absolute())
            else:
                # Download from HuggingFace
                db_path = _download_from_hf()

    if not db_path:
        raise FileNotFoundError(
            "Database not found and could not be downloaded from HuggingFace. "
            "Set SCHOLAR_DB_PATH environment variable to the correct path."
        )

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    _initialize_features(conn)
    _initialize_holonomic_entries(conn)
    _initialize_content_addresses(conn)
    _initialize_word_search(conn)
    _initialize_traditional(conn)
    _initialize_root_vectors(conn)

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


def _initialize_holonomic_entries(conn: sqlite3.Connection):
    """Create the primary holonomic_entries table."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS holonomic_entries (
            address TEXT PRIMARY KEY, -- SHA-256 UOR address
            content TEXT NOT NULL,
            phase TEXT DEFAULT 'question', -- 'question', 'hypothesis', 'validation', 'verified'
            category TEXT, -- 'linguistic', 'ncu', 'methodology', etc.
            confidence REAL DEFAULT 0.0,
            
            -- Unified Anchoring
            anchor_type TEXT, -- 'root', 'lemma', 'morpheme', 'word_type', 'word_instance', 'surah'
            anchor_ids TEXT,  -- ID or 'start, end' range or surah:ayah
            
            verification TEXT, -- 'supports', 'contradicts', 'unclear'
            notes TEXT,

            -- Verification workflow
            verse_queue TEXT, -- JSON array of references
            verse_current_index INTEGER DEFAULT 0,
            
            -- Activity tracking
            last_activity TEXT -- ISO 8601 timestamp
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_he_anchor ON holonomic_entries(anchor_type, anchor_ids)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_he_activity ON holonomic_entries(last_activity)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_he_category ON holonomic_entries(category)")


def _initialize_content_addresses(conn: sqlite3.Connection):
    """Create the mapping table for UOR addresses."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS content_addresses (
            entity_type TEXT NOT NULL, -- 'verse', 'root', 'word_type', 'holonomic_entry'
            entity_id TEXT NOT NULL,   -- e.g., '12:31' or feature_id
            address TEXT NOT NULL,      -- SHA-256
            PRIMARY KEY (entity_type, entity_id)
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ca_address ON content_addresses(address)")


def _initialize_word_search(conn: sqlite3.Connection):
    """Ensure indexes on words and compositional tables (idempotent)."""
    # Check if tables exist before creating indexes
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='word_instances'")
    if cursor.fetchone():
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_words_verse ON word_instances(verse_surah, verse_ayah, word_index)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_words_global ON word_instances(global_index)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_words_type ON word_instances(word_type_id)"
        )
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='word_type_morphemes'")
    if cursor.fetchone():
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

def _initialize_root_vectors(conn: sqlite3.Connection):
    """Create the root_vectors cache table."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS root_vectors (
            root_id INTEGER PRIMARY KEY,
            profile BLOB NOT NULL, -- Compressed numpy array
            distributional_weight REAL,
            last_updated TEXT,
            FOREIGN KEY (root_id) REFERENCES features(id)
        )"""
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rv_weight ON root_vectors(distributional_weight)")
