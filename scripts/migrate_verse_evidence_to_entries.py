"""Migrate verse_evidence rows into entries + entry_dependencies, then drop the table.

Strategy:
1. verse_evidence rows WITH notes (122) -> new entries
   - content = notes text
   - scope_type = 'verse', scope_value = 'surah:ayah'
   - phase = inherited from parent entry
   - category = inherited from parent entry
   - Linked to parent via entry_dependencies with appropriate type
2. verse_evidence rows WITHOUT notes (71) -> deleted (no useful data)
3. Drop verse_evidence table + indexes
"""

import io
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlite3

DB_PATH = Path(__file__).resolve().parent.parent / 'data' / 'kalima.db'


def _now():
    return datetime.now(timezone.utc).isoformat()


def migrate():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")  # We're restructuring

    # ── Step 0: Verify verse_evidence exists ──
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    if 'verse_evidence' not in tables:
        print("verse_evidence table does not exist — nothing to migrate")
        return

    # ── Step 1: Get all verse_evidence rows WITH notes ──
    noted_rows = conn.execute("""
        SELECT ve.id, ve.entry_id, ve.surah, ve.ayah, ve.verification, ve.notes, ve.created_at,
               e.phase AS parent_phase, e.category AS parent_category
        FROM verse_evidence ve
        JOIN entries e ON e.id = ve.entry_id
        WHERE ve.notes IS NOT NULL AND ve.notes != ''
        ORDER BY ve.entry_id, ve.surah, ve.ayah
    """).fetchall()

    empty_count = conn.execute(
        "SELECT count(*) FROM verse_evidence WHERE notes IS NULL OR notes = ''"
    ).fetchone()[0]

    total = conn.execute("SELECT count(*) FROM verse_evidence").fetchone()[0]

    print(f"verse_evidence: {total} total, {len(noted_rows)} with notes, {empty_count} empty")

    # ── Step 2: Find the next available entry ID ──
    max_entry_num = conn.execute(
        "SELECT MAX(CAST(SUBSTR(id, 7) AS INTEGER)) FROM entries WHERE id LIKE 'entry_%'"
    ).fetchone()[0] or 0
    next_id = max_entry_num + 1

    # Map verification -> dependency_type
    VERIFICATION_TO_DEP = {
        'supports': 'supports',
        'contradicts': 'contradicts',
        'unclear': 'related',
        'cited': 'related',
    }

    now = _now()
    created = 0
    deps_created = 0

    for row in noted_rows:
        entry_id = f"entry_{next_id}"
        next_id += 1

        scope_value = f"{row['surah']}:{row['ayah']}"
        dep_type = VERIFICATION_TO_DEP.get(row['verification'], 'related')

        # Create the new entry
        conn.execute(
            """INSERT INTO entries (id, content, phase, category, scope_type, scope_value, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'verse', ?, ?, ?)""",
            (entry_id, row['notes'], row['parent_phase'], row['parent_category'],
             scope_value, row['created_at'] or now, now)
        )
        created += 1

        # Link to parent entry
        conn.execute(
            """INSERT INTO entry_dependencies (entry_id, depends_on_entry_id, dependency_type, created_at)
               VALUES (?, ?, ?, ?)""",
            (entry_id, row['entry_id'], dep_type, now)
        )
        deps_created += 1

    print(f"Created {created} new entries (entry_{max_entry_num + 1} through entry_{next_id - 1})")
    print(f"Created {deps_created} entry_dependencies links")

    # ── Step 3: Drop verse_evidence ──
    conn.execute("DROP INDEX IF EXISTS idx_verse_evidence_entry")
    conn.execute("DROP INDEX IF EXISTS idx_verse_evidence_verse")
    conn.execute("DROP INDEX IF EXISTS idx_verse_evidence_verification")
    conn.execute("DROP TABLE IF EXISTS verse_evidence")
    print("Dropped verse_evidence table and indexes")

    # ── Step 4: Commit and vacuum ──
    conn.commit()
    conn.execute("VACUUM")
    print("Committed and vacuumed")

    # ── Step 5: Verify ──
    new_total = conn.execute("SELECT count(*) FROM entries").fetchone()[0]
    new_deps = conn.execute("SELECT count(*) FROM entry_dependencies").fetchone()[0]
    verse_scoped = conn.execute(
        "SELECT count(*) FROM entries WHERE scope_type = 'verse'"
    ).fetchone()[0]

    print(f"\nVerification:")
    print(f"  Total entries: {new_total}")
    print(f"  Verse-scoped entries: {verse_scoped}")
    print(f"  Total entry_dependencies: {new_deps}")

    # Confirm verse_evidence is gone
    tables_after = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert 'verse_evidence' not in tables_after, "verse_evidence table still exists!"
    print("  verse_evidence table confirmed removed")

    conn.close()
    print("\nMigration complete!")


if __name__ == '__main__':
    migrate()
