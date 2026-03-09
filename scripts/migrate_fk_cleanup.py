"""Migration: add FK constraints, drop dead columns, remove duplicate indexes.

Changes:
1. Recreate `dependencies` with FK constraints to entries(id)
2. Recreate `morphemes` with FK on word_id -> words(id) and explicit PK
3. Recreate `ref_features` without buckwalter/extra columns
4. Recreate `entries` with feature_id FK -> ref_features(id)
5. Remove duplicate indexes on dependencies
"""

import shutil
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"
BACKUP_PATH = DB_PATH.with_suffix(".db.bak_fk_cleanup")


def migrate():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}")

    # Backup
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"Backup: {BACKUP_PATH}")

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")  # Must be OFF during table recreation

    # --- 1. Recreate ref_features (drop buckwalter, extra) ---
    print("\n=== Recreating ref_features (dropping buckwalter, extra) ===")
    count_before = conn.execute("SELECT COUNT(*) FROM ref_features").fetchone()[0]

    conn.execute("""
        CREATE TABLE ref_features_new (
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
    conn.execute("""
        INSERT INTO ref_features_new (id, feature_type, category, lookup_key, label_ar, label_en, frequency)
        SELECT id, feature_type, category, lookup_key, label_ar, label_en, frequency
        FROM ref_features
    """)
    count_after = conn.execute("SELECT COUNT(*) FROM ref_features_new").fetchone()[0]
    assert count_before == count_after, f"ref_features row count mismatch: {count_before} vs {count_after}"

    conn.execute("DROP TABLE ref_features")
    conn.execute("ALTER TABLE ref_features_new RENAME TO ref_features")
    # Recreate indexes
    conn.execute("CREATE INDEX idx_ref_features_type ON ref_features(feature_type)")
    conn.execute("CREATE INDEX idx_ref_features_lookup ON ref_features(feature_type, lookup_key)")
    conn.execute("CREATE INDEX idx_ref_features_type_cat ON ref_features(feature_type, category)")
    print(f"  ref_features: {count_after} rows, buckwalter/extra dropped")

    # --- 2. Recreate entries (add feature_id FK) ---
    print("\n=== Recreating entries (adding feature_id FK -> ref_features) ===")
    count_before = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]

    conn.execute("""
        CREATE TABLE entries_new (
            id TEXT PRIMARY KEY,
            content TEXT,
            phase TEXT,
            category TEXT,
            created_at TEXT,
            updated_at TEXT,
            confidence REAL,
            feature_id INTEGER REFERENCES ref_features(id),
            unit_id INTEGER REFERENCES units(id),
            verse_total INTEGER,
            verse_verified INTEGER DEFAULT 0,
            verse_supports INTEGER DEFAULT 0,
            verse_contradicts INTEGER DEFAULT 0,
            verse_unclear INTEGER DEFAULT 0,
            verse_current_index INTEGER DEFAULT 0,
            verse_queue TEXT,
            verification_started_at TEXT,
            verification_updated_at TEXT
        )
    """)
    conn.execute("""
        INSERT INTO entries_new
        SELECT id, content, phase, category, created_at, updated_at, confidence,
               feature_id, unit_id, verse_total, verse_verified, verse_supports,
               verse_contradicts, verse_unclear, verse_current_index, verse_queue,
               verification_started_at, verification_updated_at
        FROM entries
    """)
    count_after = conn.execute("SELECT COUNT(*) FROM entries_new").fetchone()[0]
    assert count_before == count_after, f"entries row count mismatch: {count_before} vs {count_after}"

    conn.execute("DROP TABLE entries")
    conn.execute("ALTER TABLE entries_new RENAME TO entries")
    # Recreate indexes
    conn.execute("CREATE UNIQUE INDEX idx_entries_feature_id ON entries(feature_id) WHERE feature_id IS NOT NULL")
    conn.execute("CREATE INDEX idx_entries_unit ON entries(unit_id) WHERE unit_id IS NOT NULL")
    conn.execute("CREATE INDEX idx_entries_category ON entries(category)")
    conn.execute("CREATE INDEX idx_entries_phase ON entries(phase)")
    print(f"  entries: {count_after} rows, feature_id now FK -> ref_features(id)")

    # --- 3. Recreate dependencies (add FK constraints, deduplicate indexes) ---
    print("\n=== Recreating dependencies (adding FKs to entries) ===")
    count_before = conn.execute("SELECT COUNT(*) FROM dependencies").fetchone()[0]

    conn.execute("""
        CREATE TABLE dependencies_new (
            entry_id TEXT NOT NULL REFERENCES entries(id),
            depends_on_entry_id TEXT NOT NULL REFERENCES entries(id),
            dependency_type TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (entry_id, depends_on_entry_id, dependency_type)
        )
    """)
    conn.execute("""
        INSERT INTO dependencies_new (entry_id, depends_on_entry_id, dependency_type, created_at)
        SELECT entry_id, depends_on_entry_id, dependency_type, created_at
        FROM dependencies
    """)
    count_after = conn.execute("SELECT COUNT(*) FROM dependencies_new").fetchone()[0]
    assert count_before == count_after, f"dependencies row count mismatch: {count_before} vs {count_after}"

    conn.execute("DROP TABLE dependencies")
    conn.execute("ALTER TABLE dependencies_new RENAME TO dependencies")
    # Single set of indexes (no duplicates)
    conn.execute("CREATE INDEX idx_deps_from ON dependencies(entry_id)")
    conn.execute("CREATE INDEX idx_deps_to ON dependencies(depends_on_entry_id)")
    print(f"  dependencies: {count_after} rows, FKs added, duplicate indexes removed")

    # --- 4. Recreate morphemes (add word_id FK, explicit PK) ---
    print("\n=== Recreating morphemes (adding word_id FK -> words, PK on id) ===")
    count_before = conn.execute("SELECT COUNT(*) FROM morphemes").fetchone()[0]

    conn.execute("""
        CREATE TABLE morphemes_new (
            id TEXT PRIMARY KEY,
            word_id TEXT NOT NULL REFERENCES words(id),
            form TEXT,
            root_id INTEGER REFERENCES ref_features(id),
            lemma_id INTEGER REFERENCES ref_features(id),
            pos_id INTEGER REFERENCES ref_features(id),
            verb_form_id INTEGER REFERENCES ref_features(id),
            voice_id INTEGER REFERENCES ref_features(id),
            mood_id INTEGER REFERENCES ref_features(id),
            aspect_id INTEGER REFERENCES ref_features(id),
            person_id INTEGER REFERENCES ref_features(id),
            number_id INTEGER REFERENCES ref_features(id),
            gender_id INTEGER REFERENCES ref_features(id),
            case_value_id INTEGER REFERENCES ref_features(id),
            dependency_rel_id INTEGER REFERENCES ref_features(id),
            derived_noun_type_id INTEGER REFERENCES ref_features(id),
            state_id INTEGER REFERENCES ref_features(id),
            role_id INTEGER REFERENCES ref_features(id),
            type_id INTEGER REFERENCES ref_features(id)
        )
    """)
    conn.execute("""
        INSERT INTO morphemes_new
        SELECT * FROM morphemes
    """)
    count_after = conn.execute("SELECT COUNT(*) FROM morphemes_new").fetchone()[0]
    assert count_before == count_after, f"morphemes row count mismatch: {count_before} vs {count_after}"

    conn.execute("DROP TABLE morphemes")
    conn.execute("ALTER TABLE morphemes_new RENAME TO morphemes")
    # Recreate indexes
    conn.execute("CREATE INDEX idx_morphemes_word ON morphemes(word_id)")
    conn.execute("CREATE INDEX idx_morphemes_root_id ON morphemes(root_id)")
    conn.execute("CREATE INDEX idx_morphemes_lemma_id ON morphemes(lemma_id)")
    conn.execute("CREATE INDEX idx_morphemes_pos_id ON morphemes(pos_id)")
    conn.execute("CREATE INDEX idx_morphemes_aspect_id ON morphemes(aspect_id)")
    conn.execute("CREATE INDEX idx_morphemes_dep_rel_id ON morphemes(dependency_rel_id)")
    conn.execute("CREATE INDEX idx_morphemes_role_id ON morphemes(role_id)")
    conn.execute("CREATE INDEX idx_morphemes_type_id ON morphemes(type_id)")
    print(f"  morphemes: {count_after} rows, word_id FK -> words(id), PK on id")

    # --- 5. Commit and verify ---
    conn.commit()

    print("\n=== Verification ===")
    conn.execute("PRAGMA foreign_keys = ON")

    # FK integrity check
    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        print(f"  FK VIOLATIONS: {len(violations)}")
        for v in violations[:10]:
            print(f"    {v}")
    else:
        print("  FK integrity: PASSED (0 violations)")

    # Row counts
    for table in ('ref_features', 'entries', 'dependencies', 'morphemes', 'words', 'units', 'surahs'):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table}: {count} rows")

    # Schema verification
    print("\n=== New schemas ===")
    for table in ('ref_features', 'entries', 'dependencies', 'morphemes'):
        sql = conn.execute(f"SELECT sql FROM sqlite_master WHERE name='{table}'").fetchone()[0]
        print(f"\n{sql}")

    # Index list
    print("\n=== All indexes ===")
    for r in conn.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL ORDER BY tbl_name, name").fetchall():
        print(f"  {r[1]}.{r[0]}")

    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    migrate()
