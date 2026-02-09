"""Migration: Self-contained entries with scope and inline verification.

Changes:
1. Add scope columns to entries (scope_type, scope_value)
2. Add inline verification columns to entries
3. Unify entry_evidence + verse_evidence -> single verse_evidence table
4. Migrate 2 workflow_sessions into entry inline state
5. Drop workflow_sessions, entry_evidence, verse_entries view
"""

import json
import shutil
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"
BACKUP_PATH = DB_PATH.with_suffix(".db.bak-scope")


def main():
    if not DB_PATH.exists():
        print(f"ERROR: Database not found at {DB_PATH}")
        sys.exit(1)

    # Backup
    print(f"Backing up {DB_PATH} -> {BACKUP_PATH}")
    shutil.copy2(DB_PATH, BACKUP_PATH)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")  # Off during migration
    conn.execute("PRAGMA journal_mode = WAL")

    try:
        _step1_add_scope_columns(conn)
        _step2_add_verification_columns(conn)
        _step3_migrate_workflow_sessions(conn)
        _step4_unify_evidence(conn)
        _step5_update_inline_stats(conn)
        _step6_drop_old_tables(conn)
        _step7_create_indexes(conn)
        conn.execute("VACUUM")
        conn.commit()
        print("\nMigration complete!")
        _verify(conn)
    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        print(f"Restoring backup from {BACKUP_PATH}")
        conn.close()
        shutil.copy2(BACKUP_PATH, DB_PATH)
        raise
    finally:
        conn.close()


def _add_column(conn, table, col, col_type, default=None):
    """Silently add a column if it doesn't exist."""
    try:
        if default is not None:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type} DEFAULT {default}")
        else:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        print(f"  Added {table}.{col}")
    except sqlite3.OperationalError:
        pass  # Already exists


def _step1_add_scope_columns(conn):
    print("\n[Step 1] Adding scope columns to entries...")
    _add_column(conn, "entries", "scope_type", "TEXT")
    _add_column(conn, "entries", "scope_value", "TEXT")
    conn.commit()
    print("  Done.")


def _step2_add_verification_columns(conn):
    print("\n[Step 2] Adding inline verification columns to entries...")
    _add_column(conn, "entries", "verse_total", "INTEGER")
    _add_column(conn, "entries", "verse_verified", "INTEGER", 0)
    _add_column(conn, "entries", "verse_supports", "INTEGER", 0)
    _add_column(conn, "entries", "verse_contradicts", "INTEGER", 0)
    _add_column(conn, "entries", "verse_unclear", "INTEGER", 0)
    _add_column(conn, "entries", "verse_current_index", "INTEGER", 0)
    _add_column(conn, "entries", "verse_queue", "TEXT")
    _add_column(conn, "entries", "verification_started_at", "TEXT")
    _add_column(conn, "entries", "verification_updated_at", "TEXT")
    conn.commit()
    print("  Done.")


def _step3_migrate_workflow_sessions(conn):
    print("\n[Step 3] Migrating workflow sessions into entries...")

    sessions = conn.execute(
        """SELECT session_id, entry_id, workflow_type, current_index,
                  total_verses, linguistic_features, surah, verses_json, created_at
           FROM workflow_sessions"""
    ).fetchall()

    for s in sessions:
        entry_id = s["entry_id"]
        workflow_type = s["workflow_type"]

        # Determine scope from workflow
        if workflow_type == "pattern" and s["linguistic_features"]:
            scope_type = "pattern"
            scope_value = s["linguistic_features"]  # already JSON string
        elif workflow_type == "surah_theme" and s["surah"]:
            scope_type = "surah"
            scope_value = str(s["surah"])
        else:
            scope_type = None
            scope_value = None

        # Extract verse queue as simplified [{surah, ayah}, ...]
        verses = json.loads(s["verses_json"])
        queue = [{"surah": v["surah_number"], "ayah": v["ayah_number"]} for v in verses]
        queue_json = json.dumps(queue)

        conn.execute(
            """UPDATE entries SET
                scope_type = ?,
                scope_value = ?,
                verse_total = ?,
                verse_current_index = ?,
                verse_queue = ?,
                verification_started_at = ?
               WHERE id = ?""",
            (scope_type, scope_value, s["total_verses"],
             s["current_index"], queue_json, s["created_at"], entry_id)
        )
        print(f"  Migrated {s['session_id']} -> {entry_id} (scope={scope_type}, index={s['current_index']}/{s['total_verses']})")

    conn.commit()
    print(f"  Done. Migrated {len(sessions)} session(s).")


def _step4_unify_evidence(conn):
    print("\n[Step 4] Unifying evidence tables...")

    # Count source rows
    ee_count = conn.execute("SELECT COUNT(*) FROM entry_evidence").fetchone()[0]
    ve_count = conn.execute("SELECT COUNT(*) FROM verse_evidence").fetchone()[0]
    print(f"  entry_evidence: {ee_count} rows")
    print(f"  verse_evidence: {ve_count} rows")

    # Create new unified table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS verse_evidence_new (
            id TEXT PRIMARY KEY,
            entry_id TEXT NOT NULL,
            surah INTEGER NOT NULL,
            ayah INTEGER NOT NULL,
            verification TEXT NOT NULL DEFAULT 'cited',
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (entry_id) REFERENCES entries(id) ON DELETE CASCADE
        )
    """)

    # Migrate old verse_evidence (workflow verification results)
    conn.execute("""
        INSERT INTO verse_evidence_new (id, entry_id, surah, ayah, verification, notes, created_at)
        SELECT id, entry_id, verse_surah, verse_ayah, verification, notes, verified_at
        FROM verse_evidence
    """)
    ve_migrated = conn.execute("SELECT changes()").fetchone()[0]
    print(f"  Migrated {ve_migrated} verse_evidence rows")

    # Collect IDs already in the new table (from verse_evidence) to detect collisions
    existing_ids = set(
        r[0] for r in conn.execute("SELECT id FROM verse_evidence_new").fetchall()
    )

    # Find the max evidence number for renumbering collisions
    max_num = 0
    for r in conn.execute(
        "SELECT id FROM verse_evidence_new WHERE id LIKE 'evidence_%'"
    ).fetchall():
        try:
            num = int(r[0].split("_")[1])
            if num > max_num:
                max_num = num
        except (IndexError, ValueError):
            pass
    for r in conn.execute(
        "SELECT id FROM entry_evidence WHERE id LIKE 'evidence_%'"
    ).fetchall():
        try:
            num = int(r[0].split("_")[1])
            if num > max_num:
                max_num = num
        except (IndexError, ValueError):
            pass
    next_num = max_num + 1

    # Migrate entry_evidence with verification prefix parsing
    ee_rows = conn.execute(
        "SELECT id, entry_id, surah, ayah, notes, created_at FROM entry_evidence"
    ).fetchall()

    migrated = 0
    renumbered = 0
    for row in ee_rows:
        notes = row["notes"] or ""
        verification = "cited"

        # Parse [SUPPORTS], [CONTRADICTS], [UNCLEAR] prefixes
        if notes.startswith("[SUPPORTS]"):
            verification = "supports"
            notes = notes[len("[SUPPORTS]"):].strip()
        elif notes.startswith("[CONTRADICTS]"):
            verification = "contradicts"
            notes = notes[len("[CONTRADICTS]"):].strip()
        elif notes.startswith("[UNCLEAR]"):
            verification = "unclear"
            notes = notes[len("[UNCLEAR]"):].strip()

        # Handle ID collisions
        ev_id = row["id"]
        if ev_id in existing_ids:
            ev_id = f"evidence_{next_num}"
            next_num += 1
            renumbered += 1
            print(f"    Renumbered {row['id']} -> {ev_id} (collision)")

        conn.execute(
            """INSERT INTO verse_evidence_new (id, entry_id, surah, ayah, verification, notes, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (ev_id, row["entry_id"], row["surah"], row["ayah"],
             verification, notes if notes else None, row["created_at"])
        )
        existing_ids.add(ev_id)
        migrated += 1

    print(f"  Migrated {migrated} entry_evidence rows (parsed verification prefixes, {renumbered} renumbered)")

    total = conn.execute("SELECT COUNT(*) FROM verse_evidence_new").fetchone()[0]
    expected = ee_count + ve_count
    print(f"  Total unified rows: {total} (expected {expected})")
    if total != expected:
        raise RuntimeError(f"Row count mismatch: got {total}, expected {expected}")

    conn.commit()
    print("  Done.")


def _step5_update_inline_stats(conn):
    print("\n[Step 5] Computing inline verification stats for entries...")

    # Get entries that have verification data (supports/contradicts/unclear, not just cited)
    entries_with_verification = conn.execute("""
        SELECT entry_id,
               SUM(CASE WHEN verification = 'supports' THEN 1 ELSE 0 END) as supports,
               SUM(CASE WHEN verification = 'contradicts' THEN 1 ELSE 0 END) as contradicts,
               SUM(CASE WHEN verification = 'unclear' THEN 1 ELSE 0 END) as unclear,
               SUM(CASE WHEN verification != 'cited' THEN 1 ELSE 0 END) as verified,
               MAX(created_at) as last_verified
        FROM verse_evidence_new
        WHERE verification != 'cited'
        GROUP BY entry_id
    """).fetchall()

    updated = 0
    for row in entries_with_verification:
        conn.execute(
            """UPDATE entries SET
                verse_verified = ?,
                verse_supports = ?,
                verse_contradicts = ?,
                verse_unclear = ?,
                verification_updated_at = ?
               WHERE id = ?""",
            (row["verified"], row["supports"], row["contradicts"],
             row["unclear"], row["last_verified"], row["entry_id"])
        )
        updated += 1
        print(f"  {row['entry_id']}: +{row['supports']}/-{row['contradicts']}/?{row['unclear']} ({row['verified']} total)")

    conn.commit()
    print(f"  Done. Updated {updated} entries.")


def _step6_drop_old_tables(conn):
    print("\n[Step 6] Dropping old tables and renaming...")
    conn.execute("DROP VIEW IF EXISTS verse_entries")
    conn.execute("DROP TABLE IF EXISTS entry_evidence")
    conn.execute("DROP TABLE IF EXISTS verse_evidence")
    conn.execute("ALTER TABLE verse_evidence_new RENAME TO verse_evidence")
    conn.execute("DROP TABLE IF EXISTS workflow_sessions")
    conn.commit()
    print("  Dropped: verse_entries view, entry_evidence, old verse_evidence, workflow_sessions")
    print("  Renamed: verse_evidence_new -> verse_evidence")


def _step7_create_indexes(conn):
    print("\n[Step 7] Creating indexes...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_verse_evidence_entry ON verse_evidence(entry_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_verse_evidence_verse ON verse_evidence(surah, ayah)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_verse_evidence_verification ON verse_evidence(verification)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_entries_scope ON entries(scope_type)")
    conn.commit()
    print("  Done.")


def _verify(conn):
    print("\n--- Verification ---")

    # Check unified verse_evidence
    total = conn.execute("SELECT COUNT(*) FROM verse_evidence").fetchone()[0]
    print(f"  verse_evidence total: {total}")

    by_verification = conn.execute(
        "SELECT verification, COUNT(*) as cnt FROM verse_evidence GROUP BY verification ORDER BY cnt DESC"
    ).fetchall()
    for row in by_verification:
        print(f"    {row['verification']}: {row['cnt']}")

    # Check entries with scope
    scoped = conn.execute(
        "SELECT COUNT(*) FROM entries WHERE scope_type IS NOT NULL"
    ).fetchone()[0]
    print(f"  Entries with scope: {scoped}")

    # Check entries with verification state
    verified = conn.execute(
        "SELECT COUNT(*) FROM entries WHERE verse_verified > 0"
    ).fetchone()[0]
    print(f"  Entries with verification: {verified}")

    # Check old tables are gone
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()]
    print(f"  Tables: {', '.join(tables)}")

    views = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='view'"
    ).fetchall()]
    print(f"  Views: {', '.join(views) if views else '(none)'}")

    # Sanity checks
    assert "entry_evidence" not in tables, "entry_evidence should be dropped"
    assert "workflow_sessions" not in tables, "workflow_sessions should be dropped"
    assert "verse_entries" not in views, "verse_entries view should be dropped"
    assert "verse_evidence" in tables, "verse_evidence should exist"

    print("\n  All checks passed!")


if __name__ == "__main__":
    main()
