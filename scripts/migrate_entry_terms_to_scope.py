"""Migrate entry_terms data into entries.scope columns, then drop entry_terms table.

16 rows in entry_terms map entries to ref_features. This script:
1. Reads all entry_terms joined with ref_features
2. Groups by entry_id
3. For entries without scope: single root -> scope_type='root', multi-feature -> scope_type='pattern'
4. Skips entries that already have scope set
5. Drops entry_terms table and indexes
6. VACUUMs
"""

import json
import os
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path


def get_db_path() -> str:
    db_path = os.environ.get(
        'KALIMA_DB_PATH',
        str(Path(__file__).resolve().parent.parent / 'data' / 'database' / 'kalima.db')
    )
    if not Path(db_path).exists():
        print(f"Database not found at {db_path}")
        sys.exit(1)
    return db_path


def main():
    db_path = get_db_path()
    print(f"Database: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    # Check if entry_terms table exists
    table_check = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='entry_terms'"
    ).fetchone()
    if not table_check:
        print("entry_terms table does not exist. Nothing to migrate.")
        conn.close()
        return

    # Step 1: Read all entry_terms joined with ref_features
    rows = conn.execute("""
        SELECT et.entry_id, rf.feature_type, rf.category, rf.lookup_key
        FROM entry_terms et
        JOIN ref_features rf ON et.feature_id = rf.id
        ORDER BY et.entry_id
    """).fetchall()

    print(f"Found {len(rows)} entry_terms rows")

    # Step 2: Group by entry_id
    entry_features: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        entry_features[row['entry_id']].append({
            'feature_type': row['feature_type'],
            'category': row['category'],
            'lookup_key': row['lookup_key'],
        })

    print(f"Covering {len(entry_features)} distinct entries")

    # Step 3: Check which entries already have scope
    migrated = 0
    skipped = 0

    for entry_id, features in entry_features.items():
        existing = conn.execute(
            "SELECT scope_type, scope_value FROM entries WHERE id = ?", (entry_id,)
        ).fetchone()

        if not existing:
            print(f"  WARNING: {entry_id} not found in entries table, skipping")
            skipped += 1
            continue

        if existing['scope_type'] is not None:
            print(f"  SKIP {entry_id}: already has scope_type='{existing['scope_type']}'")
            skipped += 1
            continue

        # Determine scope from features
        roots = [f for f in features if f['feature_type'] == 'root']
        non_roots = [f for f in features if f['feature_type'] != 'root']

        if len(roots) == 1 and len(non_roots) == 0:
            # Single root -> scope_type='root'
            scope_type = 'root'
            scope_value = roots[0]['lookup_key']
            print(f"  MIGRATE {entry_id}: root -> '{scope_value}'")
        else:
            # Multi-feature -> scope_type='pattern' with JSON
            scope_type = 'pattern'
            pattern = {}
            for f in features:
                if f['feature_type'] == 'root':
                    pattern['root'] = f['lookup_key']
                elif f['feature_type'] == 'lemma':
                    pattern['lemma'] = f['lookup_key']
                elif f['feature_type'] == 'pos':
                    pattern['pos'] = f['lookup_key']
                elif f['feature_type'] == 'morph':
                    # Map category back to segment column name
                    cat_to_col = {
                        'VerbForm': 'verb_form',
                        'VerbState': 'aspect',
                        'VerbMood': 'mood',
                        'VerbVoice': 'voice',
                        'Person': 'person',
                        'Number': 'number',
                        'Gender': 'gender',
                        'NominalCase': 'case_value',
                        'NominalState': 'state',
                        'DerivedNoun': 'derived_noun_type',
                    }
                    col = cat_to_col.get(f['category'], f['category'])
                    pattern[col] = f['lookup_key']
                elif f['feature_type'] == 'dep_rel':
                    pattern['dependency_rel'] = f['lookup_key']

            scope_value = json.dumps(pattern, ensure_ascii=False)
            print(f"  MIGRATE {entry_id}: pattern -> {scope_value}")

        conn.execute(
            "UPDATE entries SET scope_type = ?, scope_value = ? WHERE id = ?",
            (scope_type, scope_value, entry_id)
        )
        migrated += 1

    conn.commit()
    print(f"\nMigrated {migrated} entries, skipped {skipped}")

    # Step 4: Drop entry_terms table
    print("\nDropping entry_terms table...")
    conn.execute("DROP INDEX IF EXISTS idx_entry_terms_feature")
    conn.execute("DROP INDEX IF EXISTS idx_entry_terms_entry")
    conn.execute("DROP TABLE IF EXISTS entry_terms")
    conn.commit()
    print("entry_terms table dropped")

    # Step 5: VACUUM
    print("Running VACUUM...")
    conn.execute("VACUUM")
    print("Done!")

    # Final verification
    table_check = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='entry_terms'"
    ).fetchone()
    assert table_check is None, "entry_terms table should be gone!"

    scoped = conn.execute(
        "SELECT count(*) FROM entries WHERE scope_type IS NOT NULL"
    ).fetchone()[0]
    print(f"\nTotal entries with scope: {scoped}")

    conn.close()


if __name__ == "__main__":
    main()
