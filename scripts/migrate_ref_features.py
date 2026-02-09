"""Migrate 5 ref_* tables into unified ref_features, rebuild entry_terms with FK.

This script:
1. Creates ref_features table and populates from ref_roots, ref_lemmas, ref_pos_tags,
   ref_morph_features, ref_dependency_rels
2. Migrates entry_terms rows to use feature_id FK instead of (term_type, term_value)
3. Drops old ref tables, ref_constituent_tags, and redundant verses table
4. Drops unused segments.pattern column

Run with: python -X utf8 scripts/migrate_ref_features.py
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "database" / "kalima.db"

# Maps old entry_terms term_type -> (feature_type, category) in ref_features
TERM_TYPE_MAP = {
    'root':      ('root', None),
    'lemma':     ('lemma', None),
    'pos':       ('pos', None),
    'verb_form': ('morph', 'VerbForm'),
    'aspect':    ('morph', 'VerbState'),
    'mood':      ('morph', 'VerbMood'),
    'voice':     ('morph', 'VerbVoice'),
    'person':    ('morph', 'Person'),
    'number':    ('morph', 'Number'),
    'gender':    ('morph', 'Gender'),
}


def main():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")

    # --- Step 0: Print current state ---
    print("=== Step 0: Current ref table counts ===")
    for table in ('ref_roots', 'ref_lemmas', 'ref_pos_tags', 'ref_morph_features', 'ref_dependency_rels'):
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            print(f"  {table}: {count}")
        except Exception:
            print(f"  {table}: NOT FOUND")

    et_count = conn.execute("SELECT COUNT(*) FROM entry_terms").fetchone()[0]
    print(f"  entry_terms: {et_count}")

    # --- Step 1: Create ref_features table ---
    print("\n=== Step 1: Creating ref_features table ===")
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

    # Check if already populated
    existing = conn.execute("SELECT COUNT(*) FROM ref_features").fetchone()[0]
    if existing > 0:
        print(f"  ref_features already has {existing} rows — skipping population")
    else:
        # --- Step 2: Populate from ref_roots ---
        print("\n=== Step 2: Populating from ref_roots ===")
        conn.execute("""
            INSERT INTO ref_features (feature_type, category, lookup_key, label_ar, label_en, buckwalter, frequency)
            SELECT 'root', NULL, root_ar, root_ar, NULL, root, frequency
            FROM ref_roots
        """)
        count = conn.execute("SELECT COUNT(*) FROM ref_features WHERE feature_type = 'root'").fetchone()[0]
        print(f"  Inserted {count} root features")

        # --- Step 3: Populate from ref_lemmas ---
        print("\n=== Step 3: Populating from ref_lemmas ===")
        conn.execute("""
            INSERT INTO ref_features (feature_type, category, lookup_key, label_ar, label_en, buckwalter, frequency)
            SELECT 'lemma', NULL, lemma_ar, lemma_ar, NULL, lemma, frequency
            FROM ref_lemmas
        """)
        count = conn.execute("SELECT COUNT(*) FROM ref_features WHERE feature_type = 'lemma'").fetchone()[0]
        print(f"  Inserted {count} lemma features")

        # --- Step 4: Populate from ref_pos_tags ---
        print("\n=== Step 4: Populating from ref_pos_tags ===")
        conn.execute("""
            INSERT INTO ref_features (feature_type, category, lookup_key, label_ar, label_en)
            SELECT 'pos', NULL, pos, pos_ar, pos_en
            FROM ref_pos_tags
        """)
        count = conn.execute("SELECT COUNT(*) FROM ref_features WHERE feature_type = 'pos'").fetchone()[0]
        print(f"  Inserted {count} pos features")

        # --- Step 5: Populate from ref_morph_features ---
        print("\n=== Step 5: Populating from ref_morph_features ===")
        # VerbMood tags need MOOD: prefix to match segments.mood values
        # Skip rows with blank tags (SpecialGroup has garbage placeholder rows)
        conn.execute("""
            INSERT INTO ref_features (feature_type, category, lookup_key, label_ar, label_en, extra)
            SELECT 'morph', category,
                CASE WHEN category = 'VerbMood' THEN 'MOOD:' || tag ELSE tag END,
                description_ar, description_en, extra
            FROM ref_morph_features
            WHERE tag IS NOT NULL AND tag != ''
        """)
        count = conn.execute("SELECT COUNT(*) FROM ref_features WHERE feature_type = 'morph'").fetchone()[0]
        print(f"  Inserted {count} morph features")

        # --- Step 6: Populate from ref_dependency_rels ---
        print("\n=== Step 6: Populating from ref_dependency_rels ===")
        conn.execute("""
            INSERT INTO ref_features (feature_type, category, lookup_key, label_ar, label_en)
            SELECT 'dep_rel', NULL, rel_en, rel_ar, rel_en
            FROM ref_dependency_rels
        """)
        count = conn.execute("SELECT COUNT(*) FROM ref_features WHERE feature_type = 'dep_rel'").fetchone()[0]
        print(f"  Inserted {count} dep_rel features")

    # Create indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ref_features_type ON ref_features(feature_type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ref_features_lookup ON ref_features(feature_type, lookup_key)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ref_features_type_cat ON ref_features(feature_type, category)")

    total = conn.execute("SELECT COUNT(*) FROM ref_features").fetchone()[0]
    print(f"\n  Total ref_features rows: {total}")

    # --- Step 7: Migrate entry_terms data ---
    print("\n=== Step 7: Migrating entry_terms rows ===")

    # Check if entry_terms already has the new schema (feature_id column)
    cols = [c["name"] for c in conn.execute("PRAGMA table_info(entry_terms)").fetchall()]
    if "feature_id" in cols:
        print("  entry_terms already has feature_id column — skipping migration")
    else:
        old_rows = conn.execute("SELECT entry_id, term_type, term_value, created_at FROM entry_terms").fetchall()
        print(f"  Found {len(old_rows)} rows to migrate")

        # Build new entry_terms table
        conn.execute("""
            CREATE TABLE entry_terms_new (
                entry_id TEXT NOT NULL,
                feature_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (entry_id, feature_id),
                FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE,
                FOREIGN KEY (feature_id) REFERENCES ref_features(id)
            )
        """)

        migrated = 0
        skipped = 0
        for row in old_rows:
            term_type = row["term_type"]
            term_value = row["term_value"]
            entry_id = row["entry_id"]
            created_at = row["created_at"]

            ft_info = TERM_TYPE_MAP.get(term_type)
            if not ft_info:
                print(f"  WARNING: Unknown term_type '{term_type}' for {entry_id}, skipping")
                skipped += 1
                continue

            feature_type, category = ft_info

            if category:
                ref_row = conn.execute(
                    "SELECT id FROM ref_features WHERE feature_type = ? AND category = ? AND lookup_key = ?",
                    (feature_type, category, term_value)
                ).fetchone()
            else:
                ref_row = conn.execute(
                    "SELECT id FROM ref_features WHERE feature_type = ? AND lookup_key = ?",
                    (feature_type, term_value)
                ).fetchone()

            if not ref_row:
                print(f"  WARNING: No ref_features match for {term_type}:{term_value} ({entry_id}), skipping")
                skipped += 1
                continue

            try:
                conn.execute(
                    "INSERT INTO entry_terms_new (entry_id, feature_id, created_at) VALUES (?, ?, ?)",
                    (entry_id, ref_row["id"], created_at)
                )
                migrated += 1
                print(f"  {entry_id} -> feature_id={ref_row['id']} ({term_type}:{term_value})")
            except sqlite3.IntegrityError:
                print(f"  Duplicate: {entry_id} -> feature_id={ref_row['id']}")
                skipped += 1

        print(f"\n  Migrated: {migrated}, Skipped: {skipped}")

        # Swap tables
        conn.execute("DROP TABLE entry_terms")
        conn.execute("ALTER TABLE entry_terms_new RENAME TO entry_terms")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_terms_feature ON entry_terms(feature_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_entry_terms_entry ON entry_terms(entry_id)")
        print("  Rebuilt entry_terms table with feature_id FK")

    # --- Step 8: Drop old ref tables ---
    print("\n=== Step 8: Dropping old ref tables ===")
    for table in ('ref_roots', 'ref_lemmas', 'ref_pos_tags', 'ref_morph_features',
                  'ref_dependency_rels', 'ref_constituent_tags'):
        try:
            conn.execute(f"DROP TABLE IF EXISTS {table}")
            print(f"  Dropped {table}")
        except Exception as e:
            print(f"  Failed to drop {table}: {e}")

    # Drop redundant verses table
    conn.execute("DROP TABLE IF EXISTS verses")
    print("  Dropped verses (redundant with verse_texts)")

    # --- Step 9: Drop unused segments.pattern column ---
    print("\n=== Step 9: Removing segments.pattern column ===")
    seg_cols = conn.execute("PRAGMA table_info(segments)").fetchall()
    seg_col_names = [c["name"] for c in seg_cols]

    if "pattern" not in seg_col_names:
        print("  segments.pattern already removed")
    else:
        keep_cols = [c for c in seg_col_names if c != "pattern"]
        col_list = ", ".join(keep_cols)
        print(f"  Keeping columns: {col_list}")

        conn.execute(f"CREATE TABLE segments_new AS SELECT {col_list} FROM segments")
        conn.execute("DROP TABLE segments")
        conn.execute("ALTER TABLE segments_new RENAME TO segments")

        # Recreate indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_segments_token ON segments(token_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_segments_root ON segments(root)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_segments_lemma ON segments(lemma)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_segments_pos ON segments(pos)")
        print("  Rebuilt segments table without pattern column")

    # --- Step 10: Verification ---
    print("\n=== Verification ===")

    total_features = conn.execute("SELECT COUNT(*) FROM ref_features").fetchone()[0]
    print(f"  ref_features total: {total_features}")

    for row in conn.execute(
        "SELECT feature_type, COUNT(*) as cnt FROM ref_features GROUP BY feature_type ORDER BY cnt DESC"
    ).fetchall():
        print(f"    {row['feature_type']}: {row['cnt']}")

    et_count = conn.execute("SELECT COUNT(*) FROM entry_terms").fetchone()[0]
    print(f"  entry_terms total: {et_count}")

    for row in conn.execute(
        """SELECT et.entry_id, rf.feature_type, rf.category, rf.lookup_key
           FROM entry_terms et JOIN ref_features rf ON et.feature_id = rf.id
           ORDER BY et.entry_id"""
    ).fetchall():
        cat = f"({row['category']})" if row['category'] else ""
        print(f"    {row['entry_id']} -> {row['feature_type']}{cat}:{row['lookup_key']}")

    # Check no old ref tables remain
    old_tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'ref_%' AND name != 'ref_features'"
    ).fetchall()
    print(f"  Old ref tables remaining: {[t['name'] for t in old_tables]}")

    # Check segments.pattern is gone
    seg_cols = [c["name"] for c in conn.execute("PRAGMA table_info(segments)").fetchall()]
    print(f"  segments.pattern removed: {'pattern' not in seg_cols}")

    # Check verses table is gone
    verses_exists = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='verses'"
    ).fetchone()[0]
    print(f"  verses table removed: {verses_exists == 0}")

    conn.commit()
    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
