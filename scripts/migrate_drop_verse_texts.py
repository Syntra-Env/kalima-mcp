"""Migration: Add normalized_text to tokens, drop verse_texts table."""

import io
import shutil
import sqlite3
import sys
from pathlib import Path

# Fix Windows encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.utils.arabic import normalize_arabic

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"
BACKUP_PATH = DB_PATH.with_suffix(".db.bak_drop_vt")


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
    before_tokens = conn.execute("SELECT count(*) FROM tokens").fetchone()[0]
    before_verses = conn.execute("SELECT count(*) FROM verse_texts").fetchone()[0]
    print(f"Before: {before_tokens} tokens, {before_verses} verses in verse_texts")

    # --- Step 2: Add normalized_text column to tokens ---
    try:
        conn.execute("ALTER TABLE tokens ADD COLUMN normalized_text TEXT")
        print("  Added normalized_text column to tokens")
    except sqlite3.OperationalError:
        print("  normalized_text column already exists on tokens")

    # --- Step 3: Populate normalized_text ---
    null_count = conn.execute(
        "SELECT count(*) FROM tokens WHERE normalized_text IS NULL"
    ).fetchone()[0]

    if null_count > 0:
        rows = conn.execute("SELECT id, text FROM tokens").fetchall()
        for r in rows:
            normalized = normalize_arabic(r['text'])
            conn.execute(
                "UPDATE tokens SET normalized_text = ? WHERE id = ?",
                (normalized, r['id'])
            )
        print(f"  Populated normalized_text for {len(rows)} tokens")
    else:
        print("  normalized_text already populated")

    # --- Step 4: Create indexes ---
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tokens_verse ON tokens(verse_surah, verse_ayah, token_index)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tokens_normalized ON tokens(normalized_text)"
    )
    print("  Created/verified indexes on tokens")

    # --- Step 5: Verify composition matches ---
    sample_verses = conn.execute(
        "SELECT surah_number, ayah_number, text FROM verse_texts ORDER BY RANDOM() LIMIT 10"
    ).fetchall()
    for v in sample_verses:
        tokens = conn.execute(
            "SELECT text FROM tokens WHERE verse_surah = ? AND verse_ayah = ? ORDER BY token_index",
            (v['surah_number'], v['ayah_number'])
        ).fetchall()
        composed = ' '.join(t['text'] for t in tokens)
        match = "OK" if composed == v['text'] else "DIFF (expected)"
        print(f"  Spot check {v['surah_number']}:{v['ayah_number']}: {match}")

    # --- Step 6: Drop verse_texts ---
    conn.execute("DROP TABLE verse_texts")
    print("  Dropped verse_texts table")

    # --- Step 7: Verify ---
    after_tokens = conn.execute("SELECT count(*) FROM tokens").fetchone()[0]
    normalized_count = conn.execute(
        "SELECT count(*) FROM tokens WHERE normalized_text IS NOT NULL"
    ).fetchone()[0]

    print(f"After: {after_tokens} tokens, {normalized_count} with normalized_text")

    if after_tokens != before_tokens:
        raise RuntimeError(f"Token count mismatch: {before_tokens} -> {after_tokens}")
    if normalized_count != after_tokens:
        raise RuntimeError(f"Not all tokens normalized: {normalized_count}/{after_tokens}")

    # Verify verse_texts is gone
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()]
    if 'verse_texts' in tables:
        raise RuntimeError("verse_texts table still exists!")
    print("  Verified: verse_texts dropped, all tokens normalized")

    # Spot check composition
    sample = conn.execute(
        "SELECT verse_surah, verse_ayah, GROUP_CONCAT(text, ' ') as text "
        "FROM (SELECT verse_surah, verse_ayah, text FROM tokens ORDER BY verse_surah, verse_ayah, token_index) "
        "GROUP BY verse_surah, verse_ayah LIMIT 3"
    ).fetchall()
    for s in sample:
        print(f"  Composed: {s['verse_surah']}:{s['verse_ayah']} = {s['text'][:60]}...")


if __name__ == "__main__":
    main()
