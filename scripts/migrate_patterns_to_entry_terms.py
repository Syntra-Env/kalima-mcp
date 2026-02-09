"""Migrate patterns and pattern_linguistic_features into entry_terms, then drop the tables.

This script:
1. Creates entry_terms links for root analysis entries (pattern_1 through pattern_9)
2. Creates entry_terms links for linguistic feature entries (pattern_38, 39, 41, 42)
3. Sets pattern_id = NULL on all entries
4. Drops patterns and pattern_linguistic_features tables
5. Removes pattern_id column from entries (via table rebuild)

Run with: python -X utf8 scripts/migrate_patterns_to_entry_terms.py
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "database" / "kalima.db"


def main():
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")  # Need this for table rebuild

    # Ensure entry_terms table exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entry_terms (
            entry_id TEXT NOT NULL,
            term_type TEXT NOT NULL,
            term_value TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (entry_id, term_type, term_value),
            FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE
        )
    """)

    # --- Step 1: Root analysis entries (pattern_1 through pattern_9) ---
    # These entries are about specific Arabic roots
    root_mappings = {
        "entry_195": "مسس",   # pattern_1: م س س
        "entry_196": "نصب",   # pattern_2: ن ص ب
        "entry_199": "اكل",   # pattern_3: أ ك ل
        "entry_200": "فتن",   # pattern_4: ف ت ن
        "entry_201": "جحم",   # pattern_5: ج ح م
        "entry_205": "فلق",   # pattern_6: ف ل ق
        "entry_206": "ظنن",   # pattern_7: ظ ن ن
        "entry_207": "دهن",   # pattern_8: د ه ن
        "entry_212": "ذنب",   # pattern_9: ذ ن ب
    }

    print("=== Step 1: Linking root analysis entries ===")
    for entry_id, root in root_mappings.items():
        # Verify root exists in ref_roots
        ref = conn.execute("SELECT root_ar FROM ref_roots WHERE root_ar = ?", (root,)).fetchone()
        if not ref:
            print(f"  WARNING: Root '{root}' not found in ref_roots, skipping {entry_id}")
            continue

        try:
            conn.execute(
                "INSERT INTO entry_terms (entry_id, term_type, term_value) VALUES (?, 'root', ?)",
                (entry_id, root),
            )
            print(f"  Linked {entry_id} -> root:{root}")
        except sqlite3.IntegrityError:
            print(f"  Already exists: {entry_id} -> root:{root}")

    # --- Step 2: Linguistic feature entries (pattern_38, 39, 41, 42) ---
    # These have data in pattern_linguistic_features that maps to entry_terms
    print("\n=== Step 2: Linking linguistic feature entries ===")

    feature_entries = {
        "pattern_38": "entry_277",  # Imperfective aspect -> pos:V, aspect:IMPF
        "pattern_39": "entry_278",  # Imperative verbs -> pos:V, aspect:IMPV
        "pattern_41": "entry_280",  # Root قول -> root:قول
        "pattern_42": "entry_302",  # Form III Active Participle -> verb_form:(III), pos:N
    }

    for pattern_id, entry_id in feature_entries.items():
        features = conn.execute(
            "SELECT feature_type, feature_value FROM pattern_linguistic_features WHERE pattern_id = ?",
            (pattern_id,),
        ).fetchall()

        for feat in features:
            ft = feat["feature_type"]
            fv = feat["feature_value"]

            # Normalize values to match segment column values
            if ft == "aspect" and fv == "imperfective":
                fv = "IMPF"
            elif ft == "aspect" and fv == "perfective":
                fv = "PERF"
            elif ft == "mood" and fv == "imperative":
                # Imperative is actually aspect IMPV, not mood
                ft = "aspect"
                fv = "IMPV"
            elif ft == "pos" and fv == "VERB":
                fv = "V"

            try:
                conn.execute(
                    "INSERT INTO entry_terms (entry_id, term_type, term_value) VALUES (?, ?, ?)",
                    (entry_id, ft, fv),
                )
                print(f"  Linked {entry_id} -> {ft}:{fv}")
            except sqlite3.IntegrityError:
                print(f"  Already exists: {entry_id} -> {ft}:{fv}")

    # --- Step 3: Semantic pattern entries (pattern_43 through 46) ---
    # These are methodology/framework entries with no linguistic features to migrate
    # They just need pattern_id cleared (handled in Step 4)
    print("\n=== Step 3: Semantic pattern entries (no features to migrate) ===")
    semantic_entries = {
        "pattern_43": "entry_557",  # NCU Framework
        "pattern_44": "entry_558",  # Organic Methodology
        "pattern_45": "entry_559",  # Self-Centric Interpretation
        "pattern_46": "entry_560",  # Falsification Workflow
    }
    for pattern_id, entry_id in semantic_entries.items():
        print(f"  {entry_id} (was {pattern_id}) - methodology/framework, no linguistic features")

    # Also set correct categories for entries that were 'uncategorized'
    category_updates = {
        "entry_277": "quranic_research",   # Imperfective aspect
        "entry_278": "quranic_research",   # Imperative verbs
        "entry_280": "root_analysis",      # Root قول
        "entry_302": "quranic_research",   # Form III Active Participle
        "entry_557": "ncu",                # NCU Framework (already ncu)
        "entry_558": "methodology",        # Organic Methodology
        "entry_559": "methodology",        # Self-Centric Interpretation
        "entry_560": "methodology",        # Falsification Workflow
    }

    print("\n=== Step 3b: Updating categories ===")
    for entry_id, category in category_updates.items():
        conn.execute("UPDATE entries SET category = ? WHERE id = ?", (category, entry_id))
        print(f"  {entry_id} -> category:{category}")

    # --- Step 4: Clear pattern_id on all entries ---
    print("\n=== Step 4: Clearing pattern_id on all entries ===")
    result = conn.execute("UPDATE entries SET pattern_id = NULL WHERE pattern_id IS NOT NULL")
    print(f"  Cleared pattern_id on {result.rowcount} entries")

    # --- Step 5: Drop pattern tables ---
    print("\n=== Step 5: Dropping pattern tables ===")
    conn.execute("DROP TABLE IF EXISTS pattern_linguistic_features")
    print("  Dropped pattern_linguistic_features")
    conn.execute("DROP TABLE IF EXISTS patterns")
    print("  Dropped patterns")

    # --- Step 6: Remove pattern_id column via table rebuild ---
    print("\n=== Step 6: Removing pattern_id column from entries ===")

    # Get current columns
    cols = conn.execute("PRAGMA table_info(entries)").fetchall()
    col_names = [c["name"] for c in cols if c["name"] != "pattern_id"]
    col_list = ", ".join(col_names)

    print(f"  Keeping columns: {col_list}")

    conn.execute(f"""
        CREATE TABLE entries_new AS
        SELECT {col_list} FROM entries
    """)

    conn.execute("DROP TABLE entries")
    conn.execute("ALTER TABLE entries_new RENAME TO entries")

    # Recreate indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_phase ON entries(phase)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_category ON entries(category)")

    print("  Rebuilt entries table without pattern_id")

    # --- Step 7: Verify ---
    print("\n=== Verification ===")

    entry_terms_count = conn.execute("SELECT COUNT(*) FROM entry_terms").fetchone()[0]
    print(f"  entry_terms rows: {entry_terms_count}")

    for row in conn.execute("SELECT * FROM entry_terms ORDER BY entry_id").fetchall():
        print(f"    {row['entry_id']} -> {row['term_type']}:{row['term_value']}")

    # Check no patterns table
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'pattern%'").fetchall()
    print(f"  Pattern tables remaining: {[t['name'] for t in tables]}")

    # Check no pattern_id column
    cols = conn.execute("PRAGMA table_info(entries)").fetchall()
    col_names = [c["name"] for c in cols]
    print(f"  Entries columns: {col_names}")

    has_pattern_id = "pattern_id" in col_names
    print(f"  pattern_id column removed: {not has_pattern_id}")

    conn.commit()
    conn.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
