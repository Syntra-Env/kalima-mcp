"""Normalize segments table: replace text feature columns with integer FK references to ref_features.

This migration:
1. Inserts any missing feature values from segments into ref_features (265 lemmas with annotation markers)
2. Creates a new segments table with *_id INTEGER FK columns replacing text columns
3. Populates the FK columns by looking up ref_features.id for each text value
4. Drops old segments table, renames new one
5. Creates indexes on new FK columns

Columns normalized (13 total):
  root, lemma, pos, verb_form, aspect, mood, voice, person, number, gender,
  case_value, state, derived_noun_type, dependency_rel

Columns kept as-is:
  id, token_id, type, form, role (no ref_features counterpart)
"""

import sqlite3
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.features import TERM_TYPE_TO_FEATURE

DB_PATH = Path(__file__).resolve().parent.parent / 'data' / 'kalima.db'


def migrate():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")  # OFF during migration
    conn.execute("PRAGMA journal_mode = WAL")

    t0 = time.time()

    # ── Step 1: Insert missing feature values into ref_features ──
    print("Step 1: Inserting missing feature values into ref_features...")
    inserted_features = 0

    for col, (ft, cat) in TERM_TYPE_TO_FEATURE.items():
        if cat:
            missing = conn.execute(f"""
                SELECT DISTINCT s.{col} FROM segments s
                WHERE s.{col} IS NOT NULL
                AND s.{col} NOT IN (
                    SELECT lookup_key FROM ref_features WHERE feature_type = ? AND category = ?
                )
            """, (ft, cat)).fetchall()
        else:
            missing = conn.execute(f"""
                SELECT DISTINCT s.{col} FROM segments s
                WHERE s.{col} IS NOT NULL
                AND s.{col} NOT IN (
                    SELECT lookup_key FROM ref_features WHERE feature_type = ? AND category IS NULL
                )
            """, (ft,)).fetchall()

        for row in missing:
            val = row[0]
            # Count frequency in segments
            freq = conn.execute(f"SELECT count(*) FROM segments WHERE {col} = ?", (val,)).fetchone()[0]
            conn.execute(
                "INSERT INTO ref_features (feature_type, category, lookup_key, frequency) VALUES (?, ?, ?, ?)",
                (ft, cat, val, freq)
            )
            inserted_features += 1

    conn.commit()
    print(f"  Inserted {inserted_features} missing feature values into ref_features")

    # ── Step 2: Build lookup caches (feature_type, category, lookup_key) -> id ──
    print("Step 2: Building lookup caches...")
    lookup: dict[tuple, int] = {}
    for row in conn.execute("SELECT id, feature_type, category, lookup_key FROM ref_features").fetchall():
        key = (row['feature_type'], row['category'], row['lookup_key'])
        lookup[key] = row['id']

    print(f"  Cached {len(lookup)} ref_features entries")

    # ── Step 3: Create new segments table with FK columns ──
    print("Step 3: Creating new segments table...")

    conn.execute("""
        CREATE TABLE segments_new (
            id TEXT,
            token_id TEXT,
            type TEXT,
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
            role TEXT,
            derived_noun_type_id INTEGER REFERENCES ref_features(id),
            state_id INTEGER REFERENCES ref_features(id)
        )
    """)

    # ── Step 4: Populate new table ──
    print("Step 4: Migrating 128,219 segments...")

    # Columns to normalize (in segments column order)
    fk_cols = [
        'root', 'lemma', 'pos', 'verb_form', 'voice', 'mood', 'aspect',
        'person', 'number', 'gender', 'case_value', 'dependency_rel',
        'derived_noun_type', 'state',
    ]

    batch_size = 5000
    rows = conn.execute(
        "SELECT id, token_id, type, form, root, lemma, pos, verb_form, voice, mood, aspect, "
        "person, number, gender, case_value, dependency_rel, role, derived_noun_type, state "
        "FROM segments"
    ).fetchall()

    insert_sql = """
        INSERT INTO segments_new (
            id, token_id, type, form,
            root_id, lemma_id, pos_id, verb_form_id, voice_id, mood_id, aspect_id,
            person_id, number_id, gender_id, case_value_id, dependency_rel_id,
            role, derived_noun_type_id, state_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    batch = []
    migrated = 0
    unmatched_warnings = []

    for row in rows:
        new_row = [row['id'], row['token_id'], row['type'], row['form']]

        for col in fk_cols:
            val = row[col]
            if val is None:
                new_row.append(None)
            else:
                ft, cat = TERM_TYPE_TO_FEATURE[col]
                fk_id = lookup.get((ft, cat, val))
                if fk_id is None:
                    unmatched_warnings.append((col, val))
                    new_row.append(None)
                else:
                    new_row.append(fk_id)

        # Insert role between dependency_rel_id and derived_noun_type_id
        # Actually, let me reorder: the new_row so far is:
        # [id, token_id, type, form, root_id, lemma_id, pos_id, verb_form_id, voice_id, mood_id, aspect_id,
        #  person_id, number_id, gender_id, case_value_id, dependency_rel_id, derived_noun_type_id, state_id]
        # But we need role inserted before derived_noun_type_id
        # Let me fix the order

        # Current new_row has 4 + 14 = 18 values, we need to insert role (text) at position 16
        new_row.insert(16, row['role'])  # After dependency_rel_id (index 15), before derived_noun_type_id

        batch.append(tuple(new_row))
        migrated += 1

        if len(batch) >= batch_size:
            conn.executemany(insert_sql, batch)
            batch = []
            print(f"  Migrated {migrated}/{len(rows)} rows...")

    if batch:
        conn.executemany(insert_sql, batch)

    conn.commit()
    print(f"  Migrated {migrated} segments total")

    if unmatched_warnings:
        print(f"  WARNING: {len(unmatched_warnings)} unmatched values (set to NULL)")
        # Show unique warnings
        unique = set(unmatched_warnings)
        for col, val in sorted(unique)[:10]:
            print(f"    {col}: {val}")

    # ── Step 5: Verify row counts match ──
    print("Step 5: Verifying...")
    old_count = conn.execute("SELECT count(*) FROM segments").fetchone()[0]
    new_count = conn.execute("SELECT count(*) FROM segments_new").fetchone()[0]
    assert old_count == new_count, f"Row count mismatch: {old_count} vs {new_count}"
    print(f"  Row counts match: {old_count} == {new_count}")

    # Spot-check: verify a few FK lookups
    sample = conn.execute("""
        SELECT sn.root_id, rf.lookup_key as root_text, so.root as original_root
        FROM segments_new sn
        JOIN segments so ON sn.id = so.id
        LEFT JOIN ref_features rf ON sn.root_id = rf.id
        WHERE sn.root_id IS NOT NULL
        LIMIT 5
    """).fetchall()
    for s in sample:
        assert s['root_text'] == s['original_root'], f"FK mismatch: {s['root_text']} != {s['original_root']}"
    print(f"  Spot-check passed: FK values match original text")

    # ── Step 6: Drop old table, rename new ──
    print("Step 6: Replacing old segments table...")
    conn.execute("DROP INDEX IF EXISTS idx_segments_token")
    conn.execute("DROP INDEX IF EXISTS idx_segments_root")
    conn.execute("DROP INDEX IF EXISTS idx_segments_lemma")
    conn.execute("DROP INDEX IF EXISTS idx_segments_pos")
    conn.execute("DROP TABLE segments")
    conn.execute("ALTER TABLE segments_new RENAME TO segments")

    # ── Step 7: Create indexes ──
    print("Step 7: Creating indexes...")
    conn.execute("CREATE INDEX idx_segments_token ON segments(token_id)")
    conn.execute("CREATE INDEX idx_segments_root_id ON segments(root_id)")
    conn.execute("CREATE INDEX idx_segments_lemma_id ON segments(lemma_id)")
    conn.execute("CREATE INDEX idx_segments_pos_id ON segments(pos_id)")
    conn.execute("CREATE INDEX idx_segments_aspect_id ON segments(aspect_id)")
    conn.execute("CREATE INDEX idx_segments_dep_rel_id ON segments(dependency_rel_id)")

    conn.commit()

    elapsed = time.time() - t0
    print(f"\nDone in {elapsed:.1f}s")
    print(f"  {migrated} segments normalized")
    print(f"  {inserted_features} new ref_features added")
    print(f"  14 text columns -> 14 integer FK columns")

    # VACUUM separately (can't run inside transaction)
    print("Running VACUUM...")
    conn.execute("VACUUM")
    print("VACUUM complete")

    conn.close()


if __name__ == "__main__":
    migrate()
