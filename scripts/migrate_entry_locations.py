"""Migration: Replace units/surahs tables with entry_locations.

Migrates entries.unit_id -> entry_locations rows, then drops units and surahs tables,
and rebuilds entries without the unit_id column.

Run: python scripts/migrate_entry_locations.py
"""

import shutil
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"


def migrate(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")

    # --- Pre-migration counts ---
    before_entries = conn.execute("SELECT count(*) FROM entries").fetchone()[0]
    before_deps = conn.execute("SELECT count(*) FROM dependencies").fetchone()[0]
    entries_with_unit = conn.execute(
        "SELECT count(*) FROM entries WHERE unit_id IS NOT NULL"
    ).fetchone()[0]

    print(f"Pre-migration: {before_entries} entries, {before_deps} dependencies, "
          f"{entries_with_unit} entries with unit_id")

    # --- Step 1: Capture (entry_id, surah, ayah) for all unit_id entries ---
    location_data = conn.execute("""
        SELECT e.id AS entry_id, s.value AS surah, v.value AS ayah
        FROM entries e
        JOIN units v ON e.unit_id = v.id
        JOIN units s ON v.parent_id = s.id
        WHERE e.unit_id IS NOT NULL
    """).fetchall()
    print(f"Captured {len(location_data)} entry-location mappings")

    # --- Step 2: Create entry_locations table ---
    conn.execute("DROP TABLE IF EXISTS entry_locations")
    conn.execute("""
        CREATE TABLE entry_locations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id    TEXT NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
            surah       INTEGER NOT NULL,
            ayah_start  INTEGER,
            ayah_end    INTEGER,
            word_start  INTEGER,
            word_end    INTEGER
        )
    """)

    # --- Step 3: Populate entry_locations ---
    for row in location_data:
        conn.execute(
            """INSERT INTO entry_locations (entry_id, surah, ayah_start)
               VALUES (?, ?, ?)""",
            (row["entry_id"], row["surah"], row["ayah"]),
        )
    print(f"Inserted {len(location_data)} rows into entry_locations")

    # --- Step 4: Rebuild entries without unit_id ---
    # Get current columns (excluding unit_id)
    cols_info = conn.execute("PRAGMA table_info(entries)").fetchall()
    keep_cols = [c["name"] for c in cols_info if c["name"] != "unit_id"]
    cols_str = ", ".join(keep_cols)

    conn.execute(f"""
        CREATE TABLE entries_new (
            id TEXT PRIMARY KEY,
            content TEXT,
            phase TEXT,
            category TEXT,
            created_at TEXT,
            updated_at TEXT,
            confidence REAL,
            feature_id INTEGER,
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
    conn.execute(f"INSERT INTO entries_new ({cols_str}) SELECT {cols_str} FROM entries")

    after_new = conn.execute("SELECT count(*) FROM entries_new").fetchone()[0]
    assert after_new == before_entries, (
        f"Row count mismatch: entries_new={after_new} vs entries={before_entries}"
    )

    conn.execute("DROP TABLE entries")
    conn.execute("ALTER TABLE entries_new RENAME TO entries")

    # Recreate indexes on entries
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_entries_feature_id
        ON entries(feature_id) WHERE feature_id IS NOT NULL
    """)

    # Recreate indexes on entry_locations
    conn.execute("CREATE INDEX IF NOT EXISTS idx_el_entry ON entry_locations(entry_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_el_verse ON entry_locations(surah, ayah_start)")
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_el_unique
        ON entry_locations(entry_id, surah, COALESCE(ayah_start, 0), COALESCE(word_start, 0))
    """)

    print("Rebuilt entries table without unit_id")

    # --- Step 5: Drop units and surahs ---
    conn.execute("DROP TABLE IF EXISTS units")
    conn.execute("DROP TABLE IF EXISTS surahs")
    print("Dropped units and surahs tables")

    # --- Step 6: Verify ---
    after_entries = conn.execute("SELECT count(*) FROM entries").fetchone()[0]
    after_deps = conn.execute("SELECT count(*) FROM dependencies").fetchone()[0]
    after_locations = conn.execute("SELECT count(*) FROM entry_locations").fetchone()[0]

    assert after_entries == before_entries, (
        f"Entry count mismatch: {after_entries} vs {before_entries}"
    )
    assert after_deps == before_deps, (
        f"Dependencies count mismatch: {after_deps} vs {before_deps}"
    )
    assert after_locations == entries_with_unit, (
        f"Locations count mismatch: {after_locations} vs {entries_with_unit}"
    )

    # Verify unit_id column is gone
    cols = [c["name"] for c in conn.execute("PRAGMA table_info(entries)").fetchall()]
    assert "unit_id" not in cols, "unit_id column still exists!"

    # Verify tables are gone
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    assert "units" not in tables, "units table still exists!"
    assert "surahs" not in tables, "surahs table still exists!"
    assert "entry_locations" in tables, "entry_locations table missing!"

    # Spot check: sample entry_locations
    sample = conn.execute("""
        SELECT el.entry_id, el.surah, el.ayah_start, e.content
        FROM entry_locations el
        JOIN entries e ON e.id = el.entry_id
        LIMIT 3
    """).fetchall()
    print("\nSample entry_locations:")
    for r in sample:
        print(f"  {r['entry_id']} -> {r['surah']}:{r['ayah_start']}: "
              f"{r['content'][:60]}...")

    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    # Integrity check
    result = conn.execute("PRAGMA integrity_check").fetchone()
    print(f"\nIntegrity check: {result[0]}")

    conn.close()
    print(f"\nMigration complete: {after_entries} entries, {after_locations} locations, "
          f"{after_deps} dependencies")


if __name__ == "__main__":
    db = str(DB_PATH)
    if len(sys.argv) > 1:
        db = sys.argv[1]

    if not Path(db).exists():
        print(f"Database not found: {db}")
        sys.exit(1)

    # Backup
    backup = db + ".backup-pre-locations"
    shutil.copy2(db, backup)
    print(f"Backup: {backup}")

    migrate(db)
