"""Phase 2: Migrate verse evidence into entry_locations and drop dependencies.

Steps:
1. Add `verification` and `notes` columns to entry_locations
2. For each verse-evidence dependency (supports/contradicts/related):
   - The child entry has a location and content (notes)
   - The parent entry is what the evidence supports
   - Move: create an entry_location on the PARENT with the child's location + verification + notes
   - Delete the child entry (it was only a container)
3. For conceptual dependencies (requires/depends_on/refines):
   - These need manual re-anchoring (Phase 3), but we can report them
4. Drop the dependencies table (only after all evidence is migrated)

Run with --dry-run to preview changes without modifying the database.
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"


def migrate(conn: sqlite3.Connection, dry_run: bool = False) -> dict:
    stats = {
        "evidence_migrated": 0,
        "child_entries_deleted": 0,
        "conceptual_deps": 0,
        "deps_deleted": 0,
        "errors": [],
    }

    # Step 1: Add columns to entry_locations
    for col, coltype in [("verification", "TEXT"), ("notes", "TEXT")]:
        try:
            conn.execute(f"ALTER TABLE entry_locations ADD COLUMN {col} {coltype}")
            print(f"  Added {col} column to entry_locations.")
        except sqlite3.OperationalError:
            print(f"  {col} column already exists on entry_locations.")

    # Step 2: Migrate verse-evidence dependencies
    # These are supports/contradicts/related where the child entry has a location
    evidence_deps = conn.execute("""
        SELECT d.rowid as dep_rowid,
               d.entry_id as child_id,
               d.depends_on_entry_id as parent_id,
               d.dependency_type,
               e.content as child_content,
               el.surah, el.ayah_start, el.ayah_end, el.word_start, el.word_end
        FROM dependencies d
        JOIN entries e ON e.id = d.entry_id
        JOIN entry_locations el ON el.entry_id = d.entry_id
        WHERE d.dependency_type IN ('supports', 'contradicts', 'related')
        ORDER BY d.depends_on_entry_id, el.surah, el.ayah_start
    """).fetchall()

    print(f"\n  Found {len(evidence_deps)} verse-evidence dependencies to migrate.")

    # Map dependency_type to verification value
    dep_to_verification = {
        'supports': 'supports',
        'contradicts': 'contradicts',
        'related': 'unclear',  # 'related' was used for unclear verifications
    }

    # Track child entries to delete after migration
    child_ids_to_delete = set()
    migrated_dep_rowids = set()

    for dep in evidence_deps:
        parent_id = dep['parent_id']
        child_id = dep['child_id']
        verification = dep_to_verification.get(dep['dependency_type'], 'unclear')
        notes = dep['child_content']
        surah = dep['surah']
        ayah_start = dep['ayah_start']
        ayah_end = dep['ayah_end']
        word_start = dep['word_start']
        word_end = dep['word_end']

        # Check if parent already has this location
        existing = conn.execute("""
            SELECT id FROM entry_locations
            WHERE entry_id = ? AND surah = ?
              AND COALESCE(ayah_start, 0) = COALESCE(?, 0)
              AND COALESCE(word_start, 0) = COALESCE(?, 0)
        """, (parent_id, surah, ayah_start, word_start)).fetchone()

        if existing:
            # Update existing location with verification + notes
            if not dry_run:
                conn.execute("""
                    UPDATE entry_locations
                    SET verification = ?, notes = ?
                    WHERE id = ?
                """, (verification, notes, existing['id']))
        else:
            # Create new location on parent
            if not dry_run:
                conn.execute("""
                    INSERT OR IGNORE INTO entry_locations
                    (entry_id, surah, ayah_start, ayah_end, word_start, word_end, verification, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (parent_id, surah, ayah_start, ayah_end, word_start, word_end,
                      verification, notes))

        child_ids_to_delete.add(child_id)
        migrated_dep_rowids.add(dep['dep_rowid'])
        stats["evidence_migrated"] += 1

    # Step 3: Delete child entries (they were just evidence containers)
    for child_id in child_ids_to_delete:
        if not dry_run:
            # Delete child's locations
            conn.execute("DELETE FROM entry_locations WHERE entry_id = ?", (child_id,))
            # Delete child's dependencies (both directions)
            conn.execute(
                "DELETE FROM dependencies WHERE entry_id = ? OR depends_on_entry_id = ?",
                (child_id, child_id)
            )
            # Delete child entry itself
            conn.execute("DELETE FROM entries WHERE id = ?", (child_id,))
        stats["child_entries_deleted"] += 1

    # Step 4: Count remaining conceptual dependencies
    remaining = conn.execute("""
        SELECT d.entry_id, d.depends_on_entry_id, d.dependency_type,
               SUBSTR(e1.content, 1, 80) as from_content,
               SUBSTR(e2.content, 1, 80) as to_content
        FROM dependencies d
        JOIN entries e1 ON e1.id = d.entry_id
        JOIN entries e2 ON e2.id = d.depends_on_entry_id
        WHERE d.dependency_type IN ('requires', 'depends_on', 'refines')
        ORDER BY d.dependency_type
    """).fetchall()

    stats["conceptual_deps"] = len(remaining)

    if remaining:
        print(f"\n  {len(remaining)} conceptual dependencies remain (requires/depends_on/refines).")
        print("  These need manual re-anchoring in Phase 3:")
        for r in remaining[:10]:
            print(f"    {r['entry_id']} --{r['dependency_type']}--> {r['depends_on_entry_id']}")

    # Step 5: Delete all dependency rows (evidence ones already handled, conceptual ones too)
    if not dry_run:
        total_deps = conn.execute("SELECT COUNT(*) FROM dependencies").fetchone()[0]
        conn.execute("DELETE FROM dependencies")
        stats["deps_deleted"] = total_deps

        conn.commit()

    return stats


def main():
    dry_run = "--dry-run" in sys.argv

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")

    print(f"{'DRY RUN — ' if dry_run else ''}Phase 2: Migrate verse evidence & drop dependencies")
    print(f"Database: {DB_PATH}\n")

    stats = migrate(conn, dry_run=dry_run)

    print(f"\n--- Results ---")
    print(f"Evidence migrated to entry_locations: {stats['evidence_migrated']}")
    print(f"Child entries deleted:                {stats['child_entries_deleted']}")
    print(f"Conceptual deps (need Phase 3):       {stats['conceptual_deps']}")
    print(f"Total dependency rows deleted:         {stats['deps_deleted']}")

    if stats['errors']:
        print(f"\nErrors:")
        for e in stats['errors']:
            print(f"  {e}")

    if not dry_run:
        # Verify
        deps_left = conn.execute("SELECT COUNT(*) FROM dependencies").fetchone()[0]
        entries_left = conn.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
        locs_with_verification = conn.execute(
            "SELECT COUNT(*) FROM entry_locations WHERE verification IS NOT NULL"
        ).fetchone()[0]
        print(f"\nPost-migration verification:")
        print(f"  Dependencies remaining: {deps_left}")
        print(f"  Total entries: {entries_left}")
        print(f"  Locations with verification: {locs_with_verification}")

    conn.close()


if __name__ == "__main__":
    main()
