"""Migration: Redesign units table to pure hierarchy.

Removes redundant coordinate columns (surah, ayah, word_index, morpheme_index).
Drops unused word/morpheme units. Each unit now stores only:
  - id, type, value (its own discriminator), parent_id

Surah unit: type='surah', value=<surah_number>, parent_id=NULL
Verse unit: type='verse', value=<ayah_number>, parent_id=<surah_unit_id>
"""

import shutil
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "kalima.db"
BACKUP_PATH = DB_PATH.with_suffix(".db.bak_units_pure")


def main():
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        sys.exit(1)

    # 1. Backup
    print(f"Backing up to {BACKUP_PATH.name}...")
    shutil.copy2(DB_PATH, BACKUP_PATH)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = OFF")  # We're restructuring FKs

    # 2. Record existing entry -> unit mappings (old_unit_id -> (surah, ayah))
    print("Recording entry -> unit mappings...")
    entry_units = conn.execute(
        """SELECT e.id AS entry_id, e.unit_id, u.surah, u.ayah
           FROM entries e
           JOIN units u ON e.unit_id = u.id
           WHERE e.unit_id IS NOT NULL"""
    ).fetchall()
    entry_mappings = [(r['entry_id'], r['surah'], r['ayah']) for r in entry_units]
    print(f"  {len(entry_mappings)} entries reference verse units")

    # 3. Collect existing surah/verse data
    print("Collecting surah/verse data from old units...")
    old_surahs = conn.execute(
        "SELECT DISTINCT surah FROM units WHERE type = 'surah' ORDER BY surah"
    ).fetchall()
    surah_numbers = [r['surah'] for r in old_surahs]
    print(f"  {len(surah_numbers)} surahs")

    old_verses = conn.execute(
        "SELECT surah, ayah FROM units WHERE type = 'verse' ORDER BY surah, ayah"
    ).fetchall()
    verse_pairs = [(r['surah'], r['ayah']) for r in old_verses]
    print(f"  {len(verse_pairs)} verses")

    # 4. Drop old units table
    print("Dropping old units table...")
    # Clear entry unit_ids first to avoid FK issues
    conn.execute("UPDATE entries SET unit_id = NULL WHERE unit_id IS NOT NULL")
    conn.execute("DROP TABLE IF EXISTS units")

    # 5. Create new pure units table
    print("Creating new pure units table...")
    conn.execute("""
        CREATE TABLE units (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            type      TEXT    NOT NULL CHECK(type IN ('surah', 'verse')),
            value     INTEGER NOT NULL,
            parent_id INTEGER REFERENCES units(id),
            UNIQUE(type, parent_id, value)
        )
    """)

    # 6. Insert surah units
    print("Inserting surah units...")
    surah_id_map = {}  # surah_number -> new unit id
    for s in surah_numbers:
        conn.execute(
            "INSERT INTO units (type, value, parent_id) VALUES ('surah', ?, NULL)",
            (s,)
        )
        new_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        surah_id_map[s] = new_id

    print(f"  Inserted {len(surah_id_map)} surah units")

    # 7. Insert verse units
    print("Inserting verse units...")
    verse_id_map = {}  # (surah, ayah) -> new unit id
    verse_data = []
    for surah, ayah in verse_pairs:
        parent_id = surah_id_map[surah]
        verse_data.append(('verse', ayah, parent_id))

    conn.executemany(
        "INSERT INTO units (type, value, parent_id) VALUES (?, ?, ?)",
        verse_data
    )

    # Build the verse lookup map
    for row in conn.execute(
        """SELECT v.id, s.value AS surah, v.value AS ayah
           FROM units v
           JOIN units s ON v.parent_id = s.id
           WHERE v.type = 'verse'"""
    ).fetchall():
        verse_id_map[(row['surah'], row['ayah'])] = row['id']

    print(f"  Inserted {len(verse_id_map)} verse units")

    # 8. Restore entry -> unit mappings with new IDs
    print("Restoring entry unit_id references...")
    updated = 0
    for entry_id, surah, ayah in entry_mappings:
        new_uid = verse_id_map.get((surah, ayah))
        if new_uid:
            conn.execute("UPDATE entries SET unit_id = ? WHERE id = ?", (new_uid, entry_id))
            updated += 1
        else:
            print(f"  WARNING: No verse unit for {surah}:{ayah} (entry {entry_id})")

    print(f"  Updated {updated}/{len(entry_mappings)} entries")

    # 9. Create indexes
    print("Creating indexes...")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_units_surah ON units(value) WHERE type = 'surah'")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_units_verse ON units(parent_id, value) WHERE type = 'verse'")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_units_parent ON units(parent_id) WHERE parent_id IS NOT NULL")

    conn.commit()

    # 10. Verify
    print("\n--- Verification ---")
    total = conn.execute("SELECT count(*) FROM units").fetchone()[0]
    surah_ct = conn.execute("SELECT count(*) FROM units WHERE type = 'surah'").fetchone()[0]
    verse_ct = conn.execute("SELECT count(*) FROM units WHERE type = 'verse'").fetchone()[0]
    print(f"Total units: {total} (expected {len(surah_numbers) + len(verse_pairs)})")
    print(f"  Surah: {surah_ct} (expected {len(surah_numbers)})")
    print(f"  Verse: {verse_ct} (expected {len(verse_pairs)})")

    # Check entry FK integrity
    broken = conn.execute(
        """SELECT count(*) FROM entries e
           WHERE e.unit_id IS NOT NULL
             AND e.unit_id NOT IN (SELECT id FROM units)"""
    ).fetchone()[0]
    print(f"Broken entry unit_id FKs: {broken}")

    entries_with = conn.execute("SELECT count(*) FROM entries WHERE unit_id IS NOT NULL").fetchone()[0]
    print(f"Entries with unit_id: {entries_with} (expected {len(entry_mappings)})")

    # Sample hierarchy check
    v = conn.execute(
        """SELECT v.id, v.value AS ayah, s.value AS surah
           FROM units v
           JOIN units s ON v.parent_id = s.id
           WHERE v.type = 'verse' AND s.value = 1 AND v.value = 1"""
    ).fetchone()
    if v:
        print(f"Sample: verse 1:1 -> unit_id={v['id']}")
    else:
        print("ERROR: Could not find verse 1:1")

    # Verify no orphan types
    types = conn.execute("SELECT DISTINCT type FROM units ORDER BY type").fetchall()
    print(f"Unit types: {[t[0] for t in types]}")

    assert total == len(surah_numbers) + len(verse_pairs), "Row count mismatch"
    assert broken == 0, "Broken FK references"
    assert entries_with == len(entry_mappings), "Entry mapping count mismatch"

    print("\nMigration complete!")
    conn.close()


if __name__ == "__main__":
    main()
