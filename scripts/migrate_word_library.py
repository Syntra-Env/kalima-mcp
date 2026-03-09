"""Create word_library: deduplicate words, drop redundant text columns.

Creates the pure compositional hierarchy:
  morpheme_atoms → morpheme_library → word_morphemes → word_library → words

Steps:
1. Create word_library table (unique word forms by morpheme sequence)
2. Create word_morphemes table (composition: word_library → morpheme_library)
3. Add word_library_id to words, populate it
4. Drop morphemes table (replaced by word_morphemes)
5. Drop words.text and words.normalized_text (derivable from chain)
6. Verify text reconstruction through the full chain
"""

import shutil
import sqlite3
import sys
import time
from collections import defaultdict
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"
SAFETY_BACKUP = DB_PATH.with_suffix(".db.bak_word_library")


def migrate(conn: sqlite3.Connection, dry_run: bool = False):
    t0 = time.time()
    stats = {
        "word_library_entries": 0,
        "word_morphemes_rows": 0,
        "words_updated": 0,
        "morphemes_dropped": 0,
        "text_cols_dropped": False,
    }

    # =========================================
    # Phase 1: Compute word signatures
    # =========================================
    print("\n=== Phase 1: Compute unique word forms ===")

    # Load all morphemes grouped by word_id, ordered by morpheme id
    word_morphemes_data: dict[str, list[int]] = {}
    for m in conn.execute("SELECT word_id, library_id FROM morphemes ORDER BY id").fetchall():
        word_morphemes_data.setdefault(m['word_id'], []).append(m['library_id'])

    # Group words by their morpheme library_id sequence
    sig_to_words: dict[tuple[int, ...], list[str]] = defaultdict(list)
    for word_id, lib_ids in word_morphemes_data.items():
        sig_to_words[tuple(lib_ids)].append(word_id)

    total_words = len(word_morphemes_data)
    unique_forms = len(sig_to_words)
    print(f"  {total_words} word instances -> {unique_forms} unique forms ({total_words/unique_forms:.1f}x dedup)")

    if dry_run:
        # Show top shared forms
        top = sorted(sig_to_words.items(), key=lambda x: -len(x[1]))[:10]
        for sig, wids in top:
            w = conn.execute("SELECT text FROM words WHERE id=?", (wids[0],)).fetchone()
            print(f"  {w['text']} appears {len(wids)}x ({len(sig)} morphemes)")
        print(f"\n  [DRY RUN] Would create {unique_forms} word_library entries")
        elapsed = time.time() - t0
        print(f"\nDry run complete in {elapsed:.1f}s")
        return stats

    # =========================================
    # Phase 2: Create word_library and word_morphemes tables
    # =========================================
    print("\n=== Phase 2: Create word_library and word_morphemes ===")

    conn.execute("DROP TABLE IF EXISTS word_morphemes")
    conn.execute("DROP TABLE IF EXISTS word_library")

    conn.execute("""
        CREATE TABLE word_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT
        )
    """)

    conn.execute("""
        CREATE TABLE word_morphemes (
            word_library_id INTEGER NOT NULL REFERENCES word_library(id),
            position INTEGER NOT NULL,
            morpheme_library_id INTEGER NOT NULL REFERENCES morpheme_library(id),
            PRIMARY KEY (word_library_id, position)
        )
    """)

    # Insert word_library entries and word_morphemes
    sig_to_wl_id: dict[tuple[int, ...], int] = {}

    # Batch insert word_library entries
    conn.executemany(
        "INSERT INTO word_library DEFAULT VALUES",
        [() for _ in range(unique_forms)]
    )

    # Read back IDs
    wl_ids = [r['id'] for r in conn.execute("SELECT id FROM word_library ORDER BY id").fetchall()]

    # Map sigs to word_library IDs
    wm_batch = []
    for (sig, wl_id) in zip(sig_to_words.keys(), wl_ids):
        sig_to_wl_id[sig] = wl_id
        for pos, lib_id in enumerate(sig):
            wm_batch.append((wl_id, pos, lib_id))

    conn.executemany(
        "INSERT INTO word_morphemes (word_library_id, position, morpheme_library_id) VALUES (?, ?, ?)",
        wm_batch
    )

    conn.commit()
    stats["word_library_entries"] = unique_forms
    stats["word_morphemes_rows"] = len(wm_batch)
    print(f"  Created {unique_forms} word_library entries")
    print(f"  Created {len(wm_batch)} word_morphemes rows")

    # =========================================
    # Phase 3: Add word_library_id to words
    # =========================================
    print("\n=== Phase 3: Link words to word_library ===")

    try:
        conn.execute("ALTER TABLE words ADD COLUMN word_library_id INTEGER REFERENCES word_library(id)")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Build word_id -> word_library_id mapping
    update_batch = []
    for sig, word_ids in sig_to_words.items():
        wl_id = sig_to_wl_id[sig]
        for wid in word_ids:
            update_batch.append((wl_id, wid))

    conn.executemany("UPDATE words SET word_library_id = ? WHERE id = ?", update_batch)
    conn.commit()
    stats["words_updated"] = len(update_batch)
    print(f"  Linked {len(update_batch)} words to word_library")

    # =========================================
    # Phase 4: Drop morphemes table
    # =========================================
    print("\n=== Phase 4: Drop morphemes table ===")

    morph_count = conn.execute("SELECT COUNT(*) FROM morphemes").fetchone()[0]
    conn.execute("DROP TABLE morphemes")
    conn.commit()
    stats["morphemes_dropped"] = morph_count
    print(f"  Dropped morphemes table ({morph_count} rows)")

    # =========================================
    # Phase 5: Rebuild words table without text columns
    # =========================================
    print("\n=== Phase 5: Rebuild words table (drop text columns) ===")

    conn.execute("""
        CREATE TABLE words_new (
            id TEXT PRIMARY KEY,
            verse_surah INTEGER NOT NULL,
            verse_ayah INTEGER NOT NULL,
            word_index INTEGER NOT NULL,
            word_library_id INTEGER NOT NULL REFERENCES word_library(id)
        )
    """)

    conn.execute("""
        INSERT INTO words_new (id, verse_surah, verse_ayah, word_index, word_library_id)
        SELECT id, verse_surah, verse_ayah, word_index, word_library_id FROM words
    """)

    old_count = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    new_count = conn.execute("SELECT COUNT(*) FROM words_new").fetchone()[0]
    assert old_count == new_count, f"Row count mismatch: {old_count} vs {new_count}"

    conn.execute("DROP TABLE words")
    conn.execute("ALTER TABLE words_new RENAME TO words")

    # Recreate indexes
    conn.execute("CREATE INDEX idx_words_verse ON words(verse_surah, verse_ayah, word_index)")
    conn.execute("CREATE INDEX idx_words_library ON words(word_library_id)")

    conn.commit()
    stats["text_cols_dropped"] = True
    print(f"  Words table rebuilt: {new_count} rows, 5 columns (no text)")

    # =========================================
    # Create indexes on new tables
    # =========================================
    conn.execute("CREATE INDEX idx_wm_library ON word_morphemes(morpheme_library_id)")
    conn.commit()

    # =========================================
    # Verification
    # =========================================
    print("\n=== Verification ===")

    wl_count = conn.execute("SELECT COUNT(*) FROM word_library").fetchone()[0]
    wm_count = conn.execute("SELECT COUNT(*) FROM word_morphemes").fetchone()[0]
    w_count = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    ml_count = conn.execute("SELECT COUNT(*) FROM morpheme_library").fetchone()[0]
    ma_count = conn.execute("SELECT COUNT(*) FROM morpheme_atoms").fetchone()[0]

    print(f"  word_library: {wl_count}")
    print(f"  word_morphemes: {wm_count}")
    print(f"  words: {w_count}")
    print(f"  morpheme_library: {ml_count}")
    print(f"  morpheme_atoms: {ma_count}")

    # Verify text reconstruction for verse 1:1
    print("\n  Verse 1:1 reconstruction (full chain):")
    words_11 = conn.execute(
        "SELECT id, word_index, word_library_id FROM words "
        "WHERE verse_surah=1 AND verse_ayah=1 ORDER BY word_index"
    ).fetchall()

    reconstructed_words = []
    for w in words_11:
        morphemes = conn.execute(
            "SELECT ml.uthmani_text FROM word_morphemes wm "
            "JOIN morpheme_library ml ON wm.morpheme_library_id = ml.id "
            "WHERE wm.word_library_id = ? ORDER BY wm.position",
            (w['word_library_id'],)
        ).fetchall()
        word_text = "".join(m['uthmani_text'] or '' for m in morphemes)
        reconstructed_words.append(word_text)
        print(f"    [{w['word_index']}] {word_text}")

    verse_text = " ".join(reconstructed_words)
    print(f"  Full verse: {verse_text}")

    # Verify a few more verses
    print("\n  Spot-check verses:")
    for s, a in [(2, 255), (36, 1), (112, 1)]:
        words_v = conn.execute(
            "SELECT word_library_id FROM words "
            "WHERE verse_surah=? AND verse_ayah=? ORDER BY word_index",
            (s, a)
        ).fetchall()
        parts = []
        for w in words_v:
            morphemes = conn.execute(
                "SELECT ml.uthmani_text FROM word_morphemes wm "
                "JOIN morpheme_library ml ON wm.morpheme_library_id = ml.id "
                "WHERE wm.word_library_id = ? ORDER BY wm.position",
                (w['word_library_id'],)
            ).fetchall()
            parts.append("".join(m['uthmani_text'] or '' for m in morphemes))
        print(f"    {s}:{a} = {' '.join(parts)}")

    # Check no NULL word_library_ids
    null_wl = conn.execute("SELECT COUNT(*) FROM words WHERE word_library_id IS NULL").fetchone()[0]
    print(f"\n  Words with NULL word_library_id: {null_wl}")

    # Check referential integrity
    orphan_words = conn.execute("""
        SELECT COUNT(*) FROM words w
        LEFT JOIN word_library wl ON w.word_library_id = wl.id
        WHERE wl.id IS NULL
    """).fetchone()[0]
    print(f"  Orphan words (no library entry): {orphan_words}")

    orphan_wm = conn.execute("""
        SELECT COUNT(*) FROM word_morphemes wm
        LEFT JOIN morpheme_library ml ON wm.morpheme_library_id = ml.id
        WHERE ml.id IS NULL
    """).fetchone()[0]
    print(f"  Orphan word_morphemes (no morpheme_library): {orphan_wm}")

    elapsed = time.time() - t0
    print(f"\nMigration complete in {elapsed:.1f}s")
    return stats


def main():
    dry_run = "--dry-run" in sys.argv

    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        sys.exit(1)

    if not dry_run:
        print(f"Creating safety backup: {SAFETY_BACKUP.name}")
        shutil.copy2(DB_PATH, SAFETY_BACKUP)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("PRAGMA journal_mode = WAL")

    print(f"{'DRY RUN — ' if dry_run else ''}Create word_library")
    print(f"Database: {DB_PATH}")

    stats = migrate(conn, dry_run=dry_run)

    print(f"\n--- Summary ---")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    if not dry_run:
        print("\nRunning VACUUM...")
        conn.execute("VACUUM")
        print("Done.")

    conn.close()


if __name__ == "__main__":
    main()
