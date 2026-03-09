"""Migration: rename tokens->words, segments->morphemes, extend units hierarchy.

Steps:
1. Backup database
2. Rename tables: tokens->words, segments->morphemes
3. Rename columns: token_index->word_index, token_id->word_id
4. Rename segment IDs: seg-* -> mor-*
5. Drop/recreate indexes with new names
6. Recreate units table with extended CHECK and new columns
7. Populate word and morpheme units
8. Verify
"""

import shutil
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"
BACKUP_PATH = DB_PATH.with_suffix(".db.bak_rename")


def _table_exists(conn, name):
    return conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()[0] > 0


def _column_exists(conn, table, col):
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    return col in cols


def _index_exists(conn, name):
    return conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type='index' AND name=?", (name,)
    ).fetchone()[0] > 0


def main():
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        sys.exit(1)

    # 1. Backup
    print(f"Backing up to {BACKUP_PATH}...")
    shutil.copy2(DB_PATH, BACKUP_PATH)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("PRAGMA journal_mode = WAL")

    # Detect current state
    has_tokens = _table_exists(conn, "tokens")
    has_words = _table_exists(conn, "words")
    has_segments = _table_exists(conn, "segments")
    has_morphemes = _table_exists(conn, "morphemes")

    word_table = "words" if has_words else "tokens"
    morph_table = "morphemes" if has_morphemes else "segments"

    word_count = conn.execute(f"SELECT count(*) FROM {word_table}").fetchone()[0]
    morph_count = conn.execute(f"SELECT count(*) FROM {morph_table}").fetchone()[0]
    unit_count = conn.execute("SELECT count(*) FROM units").fetchone()[0]
    print(f"Before: {word_count} words, {morph_count} morphemes, {unit_count} units")

    # 2. Rename tables (idempotent)
    if has_tokens and not has_words:
        print("Renaming tokens -> words...")
        conn.execute("ALTER TABLE tokens RENAME TO words")

    if has_segments and not has_morphemes:
        print("Renaming segments -> morphemes...")
        conn.execute("ALTER TABLE segments RENAME TO morphemes")

    # 3. Rename columns (idempotent)
    if _column_exists(conn, "words", "token_index"):
        print("Renaming token_index -> word_index...")
        conn.execute("ALTER TABLE words RENAME COLUMN token_index TO word_index")

    if _column_exists(conn, "morphemes", "token_id"):
        print("Renaming token_id -> word_id...")
        conn.execute("ALTER TABLE morphemes RENAME COLUMN token_id TO word_id")

    # 4. Rename morpheme IDs: seg-* -> mor-*
    seg_count = conn.execute("SELECT count(*) FROM morphemes WHERE id LIKE 'seg-%'").fetchone()[0]
    if seg_count > 0:
        print(f"Renaming {seg_count} morpheme IDs (seg- -> mor-)...")
        conn.execute("UPDATE morphemes SET id = replace(id, 'seg-', 'mor-')")

    conn.commit()

    # 5. Drop old indexes, recreate with new names
    print("Recreating indexes...")
    old_indexes = [
        "idx_tokens_verse", "idx_tokens_normalized",
        "idx_segments_token", "idx_segments_root_id", "idx_segments_lemma_id",
        "idx_segments_pos_id", "idx_segments_aspect_id", "idx_segments_dep_rel_id",
        "idx_segments_role_id", "idx_segments_type_id",
    ]
    for idx in old_indexes:
        conn.execute(f"DROP INDEX IF EXISTS {idx}")

    # Create new indexes on words (idempotent)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_words_verse ON words(verse_surah, verse_ayah, word_index)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_words_normalized ON words(normalized_text)")

    # Create new indexes on morphemes (idempotent)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_morphemes_word ON morphemes(word_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_morphemes_root_id ON morphemes(root_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_morphemes_lemma_id ON morphemes(lemma_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_morphemes_pos_id ON morphemes(pos_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_morphemes_aspect_id ON morphemes(aspect_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_morphemes_dep_rel_id ON morphemes(dependency_rel_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_morphemes_role_id ON morphemes(role_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_morphemes_type_id ON morphemes(type_id)")
    conn.commit()

    # 6. Recreate units table with extended CHECK and new columns
    units_cols = [r[1] for r in conn.execute("PRAGMA table_info(units)").fetchall()]
    needs_units_rebuild = "word_index" not in units_cols

    if needs_units_rebuild:
        print("Recreating units table with extended hierarchy...")

        # Save existing data
        existing_units = conn.execute("SELECT * FROM units ORDER BY id").fetchall()
        existing_entry_unit_ids = conn.execute(
            "SELECT id, unit_id FROM entries WHERE unit_id IS NOT NULL"
        ).fetchall()
        old_units = [(dict(u)['id'], dict(u)) for u in existing_units]

        # Drop old units table and indexes
        for idx in [
            "idx_units_type", "idx_units_surah", "idx_units_parent",
            "idx_units_surah_ayah", "idx_units_surah_type",
        ]:
            conn.execute(f"DROP INDEX IF EXISTS {idx}")
        conn.execute("DROP TABLE units")

        # Create new units table
        conn.execute("""
            CREATE TABLE units (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                type      TEXT    NOT NULL CHECK(type IN ('surah', 'verse', 'word', 'morpheme')),
                surah     INTEGER NOT NULL,
                ayah      INTEGER,
                word_index INTEGER,
                morpheme_index INTEGER,
                parent_id INTEGER REFERENCES units(id),
                UNIQUE(type, surah, ayah, word_index, morpheme_index)
            )
        """)

        # Re-insert existing surah and verse units with SAME IDs
        for old_id, u in old_units:
            conn.execute(
                "INSERT INTO units (id, type, surah, ayah, word_index, morpheme_index, parent_id) "
                "VALUES (?, ?, ?, ?, NULL, NULL, ?)",
                (old_id, u['type'], u['surah'], u['ayah'], u['parent_id'])
            )
        conn.commit()

        # Verify entry unit_ids still valid
        for row in existing_entry_unit_ids:
            u = conn.execute("SELECT id FROM units WHERE id = ?", (row['unit_id'],)).fetchone()
            assert u is not None, f"Entry {row['id']} references unit_id {row['unit_id']} which doesn't exist!"
        print(f"  All {len(existing_entry_unit_ids)} entry unit_id references preserved")

    # 7. Populate word units
    existing_word_units = conn.execute("SELECT count(*) FROM units WHERE type = 'word'").fetchone()[0]
    if existing_word_units == 0:
        print("Populating word units...")

        # Build verse unit lookup: (surah, ayah) -> unit_id
        verse_units = {}
        for row in conn.execute("SELECT id, surah, ayah FROM units WHERE type = 'verse'").fetchall():
            verse_units[(row['surah'], row['ayah'])] = row['id']

        words = conn.execute(
            "SELECT DISTINCT verse_surah, verse_ayah, word_index FROM words "
            "ORDER BY verse_surah, verse_ayah, word_index"
        ).fetchall()

        word_unit_data = []
        for w in words:
            parent_id = verse_units.get((w['verse_surah'], w['verse_ayah']))
            word_unit_data.append((
                'word', w['verse_surah'], w['verse_ayah'], w['word_index'], None, parent_id
            ))

        conn.executemany(
            "INSERT INTO units (type, surah, ayah, word_index, morpheme_index, parent_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            word_unit_data
        )
        conn.commit()
        word_unit_count = conn.execute("SELECT count(*) FROM units WHERE type = 'word'").fetchone()[0]
        print(f"  Inserted {word_unit_count} word units")

    # 8. Populate morpheme units
    existing_morph_units = conn.execute("SELECT count(*) FROM units WHERE type = 'morpheme'").fetchone()[0]
    if existing_morph_units == 0:
        print("Populating morpheme units...")

        # Build word unit lookup: (surah, ayah, word_index) -> unit_id
        word_units = {}
        for row in conn.execute("SELECT id, surah, ayah, word_index FROM units WHERE type = 'word'").fetchall():
            word_units[(row['surah'], row['ayah'], row['word_index'])] = row['id']

        morphemes = conn.execute(
            "SELECT m.id, w.verse_surah, w.verse_ayah, w.word_index "
            "FROM morphemes m JOIN words w ON m.word_id = w.id "
            "ORDER BY w.verse_surah, w.verse_ayah, w.word_index, m.id"
        ).fetchall()

        morpheme_unit_data = []
        for m in morphemes:
            parts = m['id'].split('-')
            morpheme_idx = int(parts[-1])
            parent_id = word_units.get((m['verse_surah'], m['verse_ayah'], m['word_index']))
            morpheme_unit_data.append((
                'morpheme', m['verse_surah'], m['verse_ayah'], m['word_index'], morpheme_idx, parent_id
            ))

        conn.executemany(
            "INSERT INTO units (type, surah, ayah, word_index, morpheme_index, parent_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            morpheme_unit_data
        )
        conn.commit()
        morph_unit_count = conn.execute("SELECT count(*) FROM units WHERE type = 'morpheme'").fetchone()[0]
        print(f"  Inserted {morph_unit_count} morpheme units")

    # 9. Recreate indexes on units
    conn.execute("CREATE INDEX IF NOT EXISTS idx_units_type ON units(type)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_units_surah ON units(surah)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_units_parent ON units(parent_id) WHERE parent_id IS NOT NULL")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_units_surah_ayah ON units(surah, ayah) WHERE ayah IS NOT NULL")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_units_surah_type ON units(surah) WHERE type = 'surah'")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_units_word ON units(surah, ayah, word_index) WHERE type = 'word'")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_units_morpheme ON units(surah, ayah, word_index, morpheme_index) WHERE type = 'morpheme'")
    conn.commit()

    # 10. Verify
    print("\nVerification:")
    final_word_count = conn.execute("SELECT count(*) FROM words").fetchone()[0]
    final_morph_count = conn.execute("SELECT count(*) FROM morphemes").fetchone()[0]
    total_units = conn.execute("SELECT count(*) FROM units").fetchone()[0]

    print(f"  words: {final_word_count}")
    print(f"  morphemes: {final_morph_count}")
    print(f"  units: {total_units}")

    assert final_word_count == word_count, f"Word count mismatch: {final_word_count} != {word_count}"
    assert final_morph_count == morph_count, f"Morpheme count mismatch: {final_morph_count} != {morph_count}"

    for t in ['surah', 'verse', 'word', 'morpheme']:
        c = conn.execute("SELECT count(*) FROM units WHERE type = ?", (t,)).fetchone()[0]
        print(f"  units[{t}]: {c}")

    # Hierarchy check
    print("\n  Hierarchy check (Surah 1, Verse 1):")
    surah_unit = conn.execute("SELECT id FROM units WHERE type='surah' AND surah=1").fetchone()
    verse_unit = conn.execute("SELECT id FROM units WHERE type='verse' AND surah=1 AND ayah=1").fetchone()
    word_units_list = conn.execute(
        "SELECT id, word_index FROM units WHERE type='word' AND surah=1 AND ayah=1 ORDER BY word_index"
    ).fetchall()
    print(f"    Surah unit: {surah_unit['id']}")
    print(f"    Verse unit: {verse_unit['id']}")
    print(f"    Word units: {len(word_units_list)}")
    for wu in word_units_list:
        morphs = conn.execute("SELECT count(*) FROM units WHERE parent_id = ?", (wu['id'],)).fetchone()[0]
        print(f"      word[{wu['word_index']}] (unit {wu['id']}): {morphs} morphemes")

    # Verify morpheme IDs renamed
    old_seg = conn.execute("SELECT count(*) FROM morphemes WHERE id LIKE 'seg-%'").fetchone()[0]
    new_mor = conn.execute("SELECT count(*) FROM morphemes WHERE id LIKE 'mor-%'").fetchone()[0]
    print(f"\n  Morpheme IDs: {old_seg} old 'seg-' remaining, {new_mor} new 'mor-' IDs")
    assert old_seg == 0, f"Still have {old_seg} old seg- IDs!"

    # Verify column renames
    cols_words = [r[1] for r in conn.execute("PRAGMA table_info(words)").fetchall()]
    cols_morphemes = [r[1] for r in conn.execute("PRAGMA table_info(morphemes)").fetchall()]
    assert 'word_index' in cols_words, "word_index column not found"
    assert 'token_index' not in cols_words, "token_index still exists"
    assert 'word_id' in cols_morphemes, "word_id column not found"
    assert 'token_id' not in cols_morphemes, "token_id still exists"
    print("  Column renames verified")

    # Sample text composition
    text_parts = conn.execute(
        "SELECT text FROM words WHERE verse_surah = 1 AND verse_ayah = 1 ORDER BY word_index"
    ).fetchall()
    verse_text = ' '.join(r['text'] for r in text_parts)
    print(f"\n  Sample 1:1 = {verse_text}")

    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()
    print("\nMigration complete!")


if __name__ == "__main__":
    main()
