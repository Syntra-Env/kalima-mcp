"""Migration: Add unified units table, replace entries.verse_surah/verse_ayah with entries.unit_id."""

import io
import shutil
import sqlite3
import sys
from pathlib import Path

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"
BACKUP_PATH = DB_PATH.with_suffix(".db.bak_units")


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
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()


def _migrate(conn: sqlite3.Connection):
    # --- Step 1: Record pre-migration counts ---
    before_entries = conn.execute("SELECT count(*) FROM entries").fetchone()[0]
    before_deps = conn.execute("SELECT count(*) FROM dependencies").fetchone()[0]
    before_surahs = conn.execute("SELECT count(*) FROM surahs").fetchone()[0]
    before_verses = conn.execute("SELECT count(*) FROM verse_texts").fetchone()[0]
    verse_entries = conn.execute("SELECT count(*) FROM entries WHERE verse_surah IS NOT NULL").fetchone()[0]
    print(f"Before: {before_entries} entries, {before_deps} dependencies")
    print(f"  {before_surahs} surahs, {before_verses} verses, {verse_entries} verse-scoped entries")

    # --- Step 2: Create units table ---
    conn.execute("""
        CREATE TABLE IF NOT EXISTS units (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            type      TEXT    NOT NULL CHECK(type IN ('surah', 'verse')),
            surah     INTEGER NOT NULL,
            ayah      INTEGER,
            parent_id INTEGER REFERENCES units(id),
            UNIQUE(type, surah, ayah)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_units_type ON units(type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_units_surah ON units(surah)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_units_parent ON units(parent_id) WHERE parent_id IS NOT NULL")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_units_surah_ayah ON units(surah, ayah) WHERE ayah IS NOT NULL")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_units_surah_type ON units(surah) WHERE type = 'surah'")
    print("  Created units table")

    # --- Step 3: Populate surah units ---
    surah_rows = conn.execute("SELECT number FROM surahs ORDER BY number").fetchall()
    surah_unit_map = {}  # surah_number -> unit_id
    for r in surah_rows:
        conn.execute(
            "INSERT INTO units (type, surah, ayah, parent_id) VALUES ('surah', ?, NULL, NULL)",
            (r['number'],)
        )
        unit_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        surah_unit_map[r['number']] = unit_id
    print(f"  Inserted {len(surah_unit_map)} surah units")

    # --- Step 4: Populate verse units ---
    verse_rows = conn.execute(
        "SELECT surah_number, ayah_number FROM verse_texts ORDER BY surah_number, ayah_number"
    ).fetchall()
    verse_count = 0
    for r in verse_rows:
        parent_id = surah_unit_map.get(r['surah_number'])
        conn.execute(
            "INSERT INTO units (type, surah, ayah, parent_id) VALUES ('verse', ?, ?, ?)",
            (r['surah_number'], r['ayah_number'], parent_id)
        )
        verse_count += 1
    print(f"  Inserted {verse_count} verse units")

    total_units = conn.execute("SELECT count(*) FROM units").fetchone()[0]
    print(f"  Total units: {total_units}")

    # --- Step 5: Add unit_id column to entries ---
    try:
        conn.execute("ALTER TABLE entries ADD COLUMN unit_id INTEGER")
        print("  Added unit_id column to entries")
    except sqlite3.OperationalError:
        print("  unit_id column already exists")

    # --- Step 6: Populate entries.unit_id from verse_surah/verse_ayah ---
    conn.execute("""
        UPDATE entries SET unit_id = (
            SELECT u.id FROM units u
            WHERE u.type = 'verse' AND u.surah = entries.verse_surah AND u.ayah = entries.verse_ayah
        )
        WHERE entries.verse_surah IS NOT NULL
    """)
    updated = conn.execute("SELECT count(*) FROM entries WHERE unit_id IS NOT NULL").fetchone()[0]
    print(f"  Populated unit_id for {updated} entries")

    # Verify all verse entries got a unit_id
    orphaned = conn.execute(
        "SELECT count(*) FROM entries WHERE verse_surah IS NOT NULL AND unit_id IS NULL"
    ).fetchone()[0]
    if orphaned > 0:
        raise RuntimeError(f"{orphaned} verse entries failed to resolve unit_id!")

    # --- Step 7: Rebuild entries table without verse_surah/verse_ayah ---
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
        INSERT INTO entries_new (
            id, content, phase, category, created_at, updated_at,
            confidence, feature_id, unit_id,
            verse_total, verse_verified, verse_supports, verse_contradicts,
            verse_unclear, verse_current_index, verse_queue,
            verification_started_at, verification_updated_at
        )
        SELECT
            id, content, phase, category, created_at, updated_at,
            confidence, feature_id, unit_id,
            verse_total, verse_verified, verse_supports, verse_contradicts,
            verse_unclear, verse_current_index, verse_queue,
            verification_started_at, verification_updated_at
        FROM entries
    """)

    conn.execute("DROP TABLE entries")
    conn.execute("ALTER TABLE entries_new RENAME TO entries")
    print("  Rebuilt entries table (dropped verse_surah, verse_ayah; added unit_id)")

    # --- Step 8: Recreate indexes ---
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_phase ON entries(phase)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_category ON entries(category)")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_entries_feature_id ON entries(feature_id) WHERE feature_id IS NOT NULL")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_unit ON entries(unit_id) WHERE unit_id IS NOT NULL")
    print("  Recreated indexes")

    # --- Step 9: Verify ---
    after_entries = conn.execute("SELECT count(*) FROM entries").fetchone()[0]
    after_deps = conn.execute("SELECT count(*) FROM dependencies").fetchone()[0]
    after_units = conn.execute("SELECT count(*) FROM units").fetchone()[0]
    unit_entries = conn.execute("SELECT count(*) FROM entries WHERE unit_id IS NOT NULL").fetchone()[0]
    feature_entries = conn.execute("SELECT count(*) FROM entries WHERE feature_id IS NOT NULL").fetchone()[0]

    print(f"After: {after_entries} entries, {after_deps} dependencies, {after_units} units")
    print(f"  {unit_entries} entries with unit_id, {feature_entries} entries with feature_id")

    if after_entries != before_entries:
        raise RuntimeError(f"Entry count mismatch: {before_entries} -> {after_entries}")
    if after_deps != before_deps:
        raise RuntimeError(f"Dependency count mismatch: {before_deps} -> {after_deps}")

    expected_units = before_surahs + before_verses
    if after_units != expected_units:
        raise RuntimeError(f"Unit count mismatch: expected {expected_units}, got {after_units}")

    if unit_entries != verse_entries:
        raise RuntimeError(f"Unit entry count mismatch: expected {verse_entries}, got {unit_entries}")

    # Verify schema
    cols = [r[1] for r in conn.execute("PRAGMA table_info(entries)").fetchall()]
    assert "verse_surah" not in cols, "verse_surah column still exists!"
    assert "verse_ayah" not in cols, "verse_ayah column still exists!"
    assert "unit_id" in cols, "unit_id column missing!"
    assert "feature_id" in cols, "feature_id column missing!"
    print("  Schema verified: verse_surah/verse_ayah removed, unit_id present")

    # Spot check: verify a unit_id resolves correctly
    sample = conn.execute(
        "SELECT e.id, e.unit_id, u.surah, u.ayah FROM entries e JOIN units u ON e.unit_id = u.id LIMIT 3"
    ).fetchall()
    for s in sample:
        print(f"  Spot check: {s['id']} -> unit {s['unit_id']} = {s['surah']}:{s['ayah']}")

    # Verify parent_id integrity
    bad_parents = conn.execute("""
        SELECT count(*) FROM units
        WHERE type = 'verse' AND parent_id NOT IN (SELECT id FROM units WHERE type = 'surah')
    """).fetchone()[0]
    assert bad_parents == 0, f"{bad_parents} verse units have invalid parent_id!"
    print("  Parent integrity verified: all verse units have valid surah parents")


if __name__ == "__main__":
    main()
