"""Migration: Replace scope_type/scope_value with feature_id and verse_surah/verse_ayah.

Renames entry_dependencies -> dependencies.
Rebuilds entries table without scope_type/scope_value.
"""

import io
import shutil
import sqlite3
import sys
from pathlib import Path

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"
BACKUP_PATH = DB_PATH.with_suffix(".db.bak_feature_id")


def main():
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        sys.exit(1)

    # Backup
    shutil.copy2(DB_PATH, BACKUP_PATH)
    print(f"Backup created: {BACKUP_PATH}")

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")

    try:
        _migrate(conn)
        conn.commit()
        print("Migration committed successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Migration FAILED, rolled back: {e}")
        sys.exit(1)
    finally:
        conn.close()


def _migrate(conn: sqlite3.Connection):
    # --- Step 1: Count rows before ---
    before_entries = conn.execute("SELECT count(*) FROM entries").fetchone()[0]
    before_deps = conn.execute("SELECT count(*) FROM entry_dependencies").fetchone()[0]
    print(f"Before: {before_entries} entries, {before_deps} dependencies")

    # --- Step 2: Add new columns to entries ---
    for col, typedef in [
        ("feature_id", "INTEGER"),
        ("verse_surah", "INTEGER"),
        ("verse_ayah", "INTEGER"),
    ]:
        try:
            conn.execute(f"ALTER TABLE entries ADD COLUMN {col} {typedef}")
            print(f"  Added column: {col}")
        except sqlite3.OperationalError:
            print(f"  Column already exists: {col}")

    # --- Step 3: Populate feature_id for root-scoped entries ---
    root_entries = conn.execute(
        "SELECT id, scope_value FROM entries WHERE scope_type = 'root'"
    ).fetchall()

    duplicates = {}  # scope_value -> list of (entry_id, verse_verified)
    for r in root_entries:
        sv = r["scope_value"]
        verified = conn.execute(
            "SELECT verse_verified FROM entries WHERE id = ?", (r["id"],)
        ).fetchone()["verse_verified"] or 0
        duplicates.setdefault(sv, []).append((r["id"], verified))

    for scope_val, entry_list in duplicates.items():
        # Resolve to ref_features id
        ref_row = conn.execute(
            "SELECT id FROM ref_features WHERE feature_type = 'root' AND category IS NULL AND lookup_key = ?",
            (scope_val,)
        ).fetchone()
        if not ref_row:
            print(f"  WARNING: Root not found in ref_features: {scope_val}")
            continue

        feature_id = ref_row["id"]

        if len(entry_list) == 1:
            # Single entry for this root
            conn.execute(
                "UPDATE entries SET feature_id = ? WHERE id = ?",
                (feature_id, entry_list[0][0])
            )
            print(f"  Set feature_id={feature_id} for {entry_list[0][0]} (root={scope_val})")
        else:
            # Multiple entries for same root - pick the one with most evidence
            entry_list.sort(key=lambda x: x[1], reverse=True)
            canonical_id = entry_list[0][0]
            conn.execute(
                "UPDATE entries SET feature_id = ? WHERE id = ?",
                (feature_id, canonical_id)
            )
            print(f"  Set feature_id={feature_id} for canonical {canonical_id} (root={scope_val})")

            # Make others into refines dependencies
            for other_id, _ in entry_list[1:]:
                # Check if dependency already exists
                existing = conn.execute(
                    "SELECT 1 FROM entry_dependencies WHERE entry_id = ? AND depends_on_entry_id = ?",
                    (other_id, canonical_id)
                ).fetchone()
                if not existing:
                    conn.execute(
                        "INSERT INTO entry_dependencies (entry_id, depends_on_entry_id, dependency_type) VALUES (?, ?, 'refines')",
                        (other_id, canonical_id)
                    )
                    print(f"  Created refines dependency: {other_id} -> {canonical_id}")

    # --- Step 4: Populate verse_surah/verse_ayah for verse-scoped entries ---
    verse_entries = conn.execute(
        "SELECT id, scope_value FROM entries WHERE scope_type = 'verse' AND scope_value IS NOT NULL"
    ).fetchall()

    updated_verse_count = 0
    for v in verse_entries:
        parts = v["scope_value"].split(":")
        if len(parts) == 2:
            surah = int(parts[0])
            ayah = int(parts[1])
            conn.execute(
                "UPDATE entries SET verse_surah = ?, verse_ayah = ? WHERE id = ?",
                (surah, ayah, v["id"])
            )
            updated_verse_count += 1
    print(f"  Populated verse_surah/verse_ayah for {updated_verse_count} verse entries")

    # --- Step 5: Rename entry_dependencies -> dependencies ---
    conn.execute("ALTER TABLE entry_dependencies RENAME TO dependencies")
    print("  Renamed entry_dependencies -> dependencies")

    # --- Step 6: Rebuild entries table without scope_type/scope_value ---
    conn.execute("""
        CREATE TABLE entries_new (
            id TEXT PRIMARY KEY,
            content TEXT,
            phase TEXT,
            category TEXT,
            created_at TEXT,
            updated_at TEXT,
            confidence REAL,
            feature_id INTEGER UNIQUE,
            verse_surah INTEGER,
            verse_ayah INTEGER,
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
        INSERT INTO entries_new (
            id, content, phase, category, created_at, updated_at,
            confidence, feature_id, verse_surah, verse_ayah,
            verse_total, verse_verified, verse_supports, verse_contradicts,
            verse_unclear, verse_current_index, verse_queue,
            verification_started_at, verification_updated_at
        )
        SELECT
            id, content, phase, category, created_at, updated_at,
            confidence, feature_id, verse_surah, verse_ayah,
            verse_total, verse_verified, verse_supports, verse_contradicts,
            verse_unclear, verse_current_index, verse_queue,
            verification_started_at, verification_updated_at
        FROM entries
    """)

    conn.execute("DROP TABLE entries")
    conn.execute("ALTER TABLE entries_new RENAME TO entries")
    print("  Rebuilt entries table (dropped scope_type, scope_value)")

    # --- Step 7: Recreate indexes ---
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_phase ON entries(phase)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_category ON entries(category)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_entries_feature_id ON entries(feature_id) WHERE feature_id IS NOT NULL")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_verse ON entries(verse_surah, verse_ayah) WHERE verse_surah IS NOT NULL")

    # Recreate dependency indexes with new table name
    conn.execute("CREATE INDEX IF NOT EXISTS idx_deps_from ON dependencies(entry_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_deps_to ON dependencies(depends_on_entry_id)")
    print("  Recreated indexes")

    # --- Step 8: Verify ---
    after_entries = conn.execute("SELECT count(*) FROM entries").fetchone()[0]
    after_deps = conn.execute("SELECT count(*) FROM dependencies").fetchone()[0]
    print(f"After: {after_entries} entries, {after_deps} dependencies")

    if after_entries != before_entries:
        raise RuntimeError(f"Entry count mismatch: {before_entries} -> {after_entries}")
    if after_deps != before_deps:
        # deps may have grown by 1 if we added a refines dep for duplicate root
        print(f"  Note: dependency count changed ({before_deps} -> {after_deps}) due to duplicate root handling")

    # Verify no scope columns remain
    cols = [r[1] for r in conn.execute("PRAGMA table_info(entries)").fetchall()]
    assert "scope_type" not in cols, "scope_type column still exists!"
    assert "scope_value" not in cols, "scope_value column still exists!"
    assert "feature_id" in cols, "feature_id column missing!"
    assert "verse_surah" in cols, "verse_surah column missing!"
    assert "verse_ayah" in cols, "verse_ayah column missing!"
    print("  Schema verified: scope_type/scope_value removed, feature_id/verse_surah/verse_ayah present")

    # Verify feature_id entries
    feature_count = conn.execute("SELECT count(*) FROM entries WHERE feature_id IS NOT NULL").fetchone()[0]
    verse_count = conn.execute("SELECT count(*) FROM entries WHERE verse_surah IS NOT NULL").fetchone()[0]
    print(f"  {feature_count} entries with feature_id, {verse_count} entries with verse location")


if __name__ == "__main__":
    main()
