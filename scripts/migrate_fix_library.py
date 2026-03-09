"""Fix morpheme_library: restore features, rebuild with proper deduplication.

The morpheme_library is broken: referenced entries (45017+) have no features,
while the correct entries (1-23946) are orphaned. This script:

Phase 1: Restore feature columns on morphemes from backup-pre-uthmani
Phase 2: Compute uthmani_form for each morpheme (alignment algorithm)
Phase 3: Rebuild morpheme_library with proper dedup (text + features)
Phase 4: Recreate morpheme_atoms for each library entry
Phase 5: Cleanup (drop old entries, strip temp columns)

Run with --dry-run to preview without changes.
"""

import shutil
import sqlite3
import sys
import time
import unicodedata
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"
BACKUP_PATH = DB_PATH.with_suffix(".db.backup-pre-uthmani")
SAFETY_BACKUP = DB_PATH.with_suffix(".db.bak_fix_library")


# --- Uthmani alignment (from migrate_uthmani_forms.py) ---

SUBSTITUTIONS = {
    "\u0671": "\u0627",  # Alef wasla -> plain alef
    "\u06E7": "\u06E6",  # Small high yeh -> small yeh
}

MULTI_SUBSTITUTIONS = [
    ("\u0640\u0654", "\u0621"),  # tatweel + hamza-above -> standalone hamza
]


def chars_match(uthmani_ch: str, form_ch: str) -> bool:
    if uthmani_ch == form_ch:
        return True
    return SUBSTITUTIONS.get(uthmani_ch) == form_ch


def align_uthmani_to_morphemes(word_text: str, morpheme_forms: list[str]) -> list[str] | None:
    """Split Uthmani word text into segments aligned with morpheme forms."""
    if not morpheme_forms:
        return None

    concat = "".join(morpheme_forms)
    if word_text == concat:
        return list(morpheme_forms)

    boundaries = []
    pos = 0
    for form in morpheme_forms:
        boundaries.append((pos, pos + len(form)))
        pos += len(form)

    form_idx = 0
    alignments: list[int] = []

    i = 0
    while i < len(word_text):
        ch = word_text[i]

        multi_matched = False
        for uth_seq, form_seq in MULTI_SUBSTITUTIONS:
            if word_text[i:i+len(uth_seq)] == uth_seq:
                if concat[form_idx:form_idx+len(form_seq)] == form_seq:
                    for j in range(len(uth_seq)):
                        alignments.append(form_idx)
                    form_idx += len(form_seq)
                    i += len(uth_seq)
                    multi_matched = True
                    break

        if multi_matched:
            continue

        if form_idx < len(concat) and chars_match(ch, concat[form_idx]):
            alignments.append(form_idx)
            form_idx += 1
        else:
            attachpoint = form_idx if form_idx < len(concat) else len(concat) - 1
            alignments.append(attachpoint)

        i += 1

    if form_idx != len(concat):
        remaining = concat[form_idx:]
        if remaining.replace("\u0640", "") != "":
            return None

    segments = []
    for mi, (start, end) in enumerate(boundaries):
        segment_chars = []
        is_last = (mi == len(boundaries) - 1)
        for j, ch in enumerate(word_text):
            a = alignments[j]
            if start <= a < end:
                segment_chars.append(ch)
            elif is_last and a >= end:
                segment_chars.append(ch)
        segments.append("".join(segment_chars))

    return segments


# --- Atom decomposition (from migrate_to_compositional.py) ---

def is_arabic_base_letter(ch: str) -> bool:
    cat = unicodedata.category(ch)
    code = ord(ch)
    return (cat == 'Lo' or code == 0x0640) and (0x0600 <= code <= 0x06FF)


def decompose_morpheme(text: str) -> list[dict]:
    atoms = []
    current_atom = None
    for ch in text:
        if is_arabic_base_letter(ch):
            if current_atom:
                atoms.append(current_atom)
            current_atom = {"base": ch, "diacritics": ""}
        else:
            if not current_atom:
                current_atom = {"base": "", "diacritics": ""}
            current_atom["diacritics"] += ch
    if current_atom:
        atoms.append(current_atom)
    return atoms


# --- Feature column helpers ---

FEATURE_COLS = [
    'root_id', 'lemma_id', 'pos_id', 'verb_form_id', 'voice_id', 'mood_id',
    'aspect_id', 'person_id', 'number_id', 'gender_id', 'case_value_id',
    'dependency_rel_id', 'derived_noun_type_id', 'state_id', 'role_id', 'type_id',
]


def normalize_morpheme_id(mid: str) -> str:
    """Convert mor-S:A:W-M format to mor-S-A-W-M format."""
    return mid.replace(':', '-')


def feature_tuple(row) -> tuple:
    """Extract feature values as a tuple for hashing/comparison."""
    return tuple(row[col] for col in FEATURE_COLS)


def feature_is_match(a, b) -> bool:
    """Check if two feature tuples match (NULL-safe)."""
    for va, vb in zip(a, b):
        if va != vb:
            return False
    return True


# --- Main migration ---

def migrate(conn: sqlite3.Connection, backup_conn: sqlite3.Connection, dry_run: bool = False):
    t0 = time.time()
    stats = {
        "features_restored": 0,
        "uthmani_aligned": 0,
        "uthmani_perfect": 0,
        "uthmani_failed": 0,
        "library_entries_created": 0,
        "atoms_created": 0,
        "old_library_deleted": 0,
        "old_atoms_deleted": 0,
    }

    # =========================================
    # Phase 1: Restore features from backup
    # =========================================
    print("\n=== Phase 1: Restore feature columns from backup ===")

    # Add columns to morphemes
    for col in ['form'] + FEATURE_COLS:
        coltype = 'TEXT' if col == 'form' else 'INTEGER'
        try:
            conn.execute(f"ALTER TABLE morphemes ADD COLUMN {col} {coltype}")
        except sqlite3.OperationalError:
            pass

    # Build backup lookup: normalized_id -> (form, features...)
    print("  Loading backup morphemes...")
    backup_data = {}
    for row in backup_conn.execute(
        "SELECT id, form, " + ", ".join(FEATURE_COLS) + " FROM morphemes"
    ).fetchall():
        norm_id = normalize_morpheme_id(row['id'])
        backup_data[norm_id] = dict(row)

    print(f"  Loaded {len(backup_data)} backup morphemes")

    # Update current morphemes from backup
    print("  Restoring features...")
    current_morphemes = conn.execute("SELECT id FROM morphemes").fetchall()

    update_sql = f"""
        UPDATE morphemes SET form = ?,
            {', '.join(f'{col} = ?' for col in FEATURE_COLS)}
        WHERE id = ?
    """

    batch = []
    unmatched = []
    for row in current_morphemes:
        mid = row['id']
        norm = normalize_morpheme_id(mid)
        bdata = backup_data.get(norm) or backup_data.get(mid)

        if not bdata:
            unmatched.append(mid)
            continue

        params = [bdata['form']] + [bdata[col] for col in FEATURE_COLS] + [mid]
        batch.append(params)

        if len(batch) >= 5000:
            if not dry_run:
                conn.executemany(update_sql, batch)
            stats["features_restored"] += len(batch)
            batch = []

    if batch:
        if not dry_run:
            conn.executemany(update_sql, batch)
        stats["features_restored"] += len(batch)

    if not dry_run:
        conn.commit()

    print(f"  Restored features for {stats['features_restored']} morphemes")
    if unmatched:
        print(f"  WARNING: {len(unmatched)} morphemes had no backup match")
        for m in unmatched[:5]:
            print(f"    {m}")

    # =========================================
    # Phase 2: Compute uthmani_form
    # =========================================
    print("\n=== Phase 2: Compute uthmani_form ===")

    try:
        conn.execute("ALTER TABLE morphemes ADD COLUMN uthmani_form TEXT")
    except sqlite3.OperationalError:
        pass

    # Load ALL data into memory for speed (no per-word queries)
    print("  Loading words and morphemes into memory...")
    all_words = {}
    for w in conn.execute("SELECT id, text FROM words").fetchall():
        all_words[w['id']] = w['text']

    # Group morphemes by word_id
    word_morphemes: dict[str, list[tuple[str, str]]] = {}
    for m in conn.execute("SELECT id, word_id, form FROM morphemes ORDER BY id").fetchall():
        word_morphemes.setdefault(m['word_id'], []).append((m['id'], m['form']))

    print(f"  Loaded {len(all_words)} words, {sum(len(v) for v in word_morphemes.values())} morphemes")

    # Compute uthmani_form for each word's morphemes
    update_batch: list[tuple] = []  # (uthmani_form, morpheme_id)

    for word_id, morphemes in word_morphemes.items():
        word_text = all_words.get(word_id)
        if not word_text:
            continue

        forms = [form for _, form in morphemes]
        mor_ids = [mid for mid, _ in morphemes]

        if any(f is None for f in forms):
            stats["uthmani_failed"] += 1
            continue

        concat = "".join(forms)
        if word_text == concat:
            stats["uthmani_perfect"] += 1
            for mid, form in zip(mor_ids, forms):
                update_batch.append((form, mid))
        else:
            segments = align_uthmani_to_morphemes(word_text, forms)
            if segments and "".join(segments) == word_text:
                stats["uthmani_aligned"] += 1
                for mid, seg in zip(mor_ids, segments):
                    update_batch.append((seg, mid))
            else:
                stats["uthmani_failed"] += 1
                for mid, form in zip(mor_ids, forms):
                    update_batch.append((form, mid))

    if not dry_run and update_batch:
        print(f"  Writing {len(update_batch)} uthmani_form values...")
        conn.executemany("UPDATE morphemes SET uthmani_form = ? WHERE id = ?", update_batch)
        conn.commit()

    print(f"  Perfect match: {stats['uthmani_perfect']}")
    print(f"  Aligned: {stats['uthmani_aligned']}")
    print(f"  Failed (used form fallback): {stats['uthmani_failed']}")

    # =========================================
    # Phase 3: Rebuild morpheme_library
    # =========================================
    print("\n=== Phase 3: Rebuild morpheme_library ===")

    # Collect all unique (uthmani_form, features) combos
    all_morphemes = conn.execute(
        "SELECT id, uthmani_form, " + ", ".join(FEATURE_COLS) + " FROM morphemes"
    ).fetchall()

    # Build dedup map: (uthmani_form, *features) -> list of morpheme ids
    sig_to_morphemes: dict[tuple, list[str]] = {}
    for m in all_morphemes:
        sig = (m['uthmani_form'],) + tuple(m[col] for col in FEATURE_COLS)
        sig_to_morphemes.setdefault(sig, []).append(m['id'])

    unique_forms = len(sig_to_morphemes)
    total_morphemes = len(all_morphemes)
    print(f"  {total_morphemes} morpheme instances -> {unique_forms} unique forms ({total_morphemes/unique_forms:.1f}x dedup)")

    if dry_run:
        print("  [DRY RUN] Would rebuild library with", unique_forms, "entries")
        elapsed = time.time() - t0
        print(f"\nDry run complete in {elapsed:.1f}s")
        return stats

    # Drop old library and atoms, recreate
    print("  Dropping old library and atoms...")
    old_lib_count = conn.execute("SELECT COUNT(*) FROM morpheme_library").fetchone()[0]
    old_atom_count = conn.execute("SELECT COUNT(*) FROM morpheme_atoms").fetchone()[0]
    stats["old_library_deleted"] = old_lib_count
    stats["old_atoms_deleted"] = old_atom_count

    conn.execute("DELETE FROM morpheme_atoms")
    conn.execute("DELETE FROM morpheme_library")
    # Reset autoincrement
    conn.execute("DELETE FROM sqlite_sequence WHERE name = 'morpheme_library'")
    conn.execute("DELETE FROM sqlite_sequence WHERE name = 'morpheme_atoms'")
    conn.commit()

    # Insert new library entries
    print(f"  Creating {unique_forms} library entries...")

    lib_insert_sql = (
        "INSERT INTO morpheme_library (uthmani_text, " + ", ".join(FEATURE_COLS) + ") "
        "VALUES (?, " + ", ".join(["?"] * len(FEATURE_COLS)) + ")"
    )

    # Batch insert all library entries
    lib_rows = []
    sig_order = list(sig_to_morphemes.keys())
    for sig in sig_order:
        uthmani_text = sig[0]
        features = sig[1:]
        lib_rows.append([uthmani_text] + list(features))

    conn.executemany(lib_insert_sql, lib_rows)
    conn.commit()
    stats["library_entries_created"] = len(lib_rows)

    # Build sig -> lib_id map by reading back in insertion order
    # (AUTOINCREMENT guarantees sequential IDs)
    all_lib = conn.execute(
        "SELECT id, uthmani_text, " + ", ".join(FEATURE_COLS) + " FROM morpheme_library ORDER BY id"
    ).fetchall()

    sig_to_lib_id: dict[tuple, int] = {}
    for lib_row in all_lib:
        sig = (lib_row['uthmani_text'],) + tuple(lib_row[col] for col in FEATURE_COLS)
        sig_to_lib_id[sig] = lib_row['id']

    # Verify all sigs mapped
    unmapped = [s for s in sig_order if s not in sig_to_lib_id]
    if unmapped:
        print(f"  WARNING: {len(unmapped)} signatures unmapped after library insert!")
        # This can happen with NULL handling in tuples. Fall back to slower matching.
        for sig in unmapped:
            uthmani_text = sig[0]
            features = sig[1:]
            # Build NULL-safe WHERE clause
            conditions = ["uthmani_text IS ?"]
            params = [uthmani_text]
            for i, col in enumerate(FEATURE_COLS):
                conditions.append(f"{col} IS ?")
                params.append(features[i])
            row = conn.execute(
                "SELECT id FROM morpheme_library WHERE " + " AND ".join(conditions),
                params
            ).fetchone()
            if row:
                sig_to_lib_id[sig] = row['id']
            else:
                print(f"    FATAL: Could not find library entry for sig {sig[:3]}...")

    # Create atoms in bulk
    print(f"  Creating atoms...")
    atom_batch = []
    for sig, lib_id in sig_to_lib_id.items():
        uthmani_text = sig[0]
        if uthmani_text:
            atoms = decompose_morpheme(uthmani_text)
            for i, atom in enumerate(atoms):
                atom_batch.append((lib_id, i, atom['base'], atom['diacritics']))

    conn.executemany(
        "INSERT INTO morpheme_atoms (morpheme_library_id, position, base_letter, diacritics) "
        "VALUES (?, ?, ?, ?)",
        atom_batch
    )
    conn.commit()
    stats["atoms_created"] = len(atom_batch)

    # =========================================
    # Phase 4: Update morphemes.library_id
    # =========================================
    print("\n=== Phase 4: Update morphemes.library_id ===")

    batch = []
    for sig, morph_ids in sig_to_morphemes.items():
        lib_id = sig_to_lib_id[sig]
        for mid in morph_ids:
            batch.append((lib_id, mid))

        if len(batch) >= 5000:
            conn.executemany("UPDATE morphemes SET library_id = ? WHERE id = ?", batch)
            batch = []

    if batch:
        conn.executemany("UPDATE morphemes SET library_id = ? WHERE id = ?", batch)

    conn.commit()
    print(f"  Updated library_id for {total_morphemes} morphemes")

    # =========================================
    # Phase 5: Strip temporary columns
    # =========================================
    print("\n=== Phase 5: Rebuild morphemes (strip temp columns) ===")

    # Recreate morphemes with just (id, word_id, library_id)
    conn.execute("""
        CREATE TABLE morphemes_clean (
            id TEXT PRIMARY KEY,
            word_id TEXT NOT NULL REFERENCES words(id),
            library_id INTEGER NOT NULL REFERENCES morpheme_library(id)
        )
    """)

    conn.execute("""
        INSERT INTO morphemes_clean (id, word_id, library_id)
        SELECT id, word_id, library_id FROM morphemes
    """)

    # Verify row count
    old_count = conn.execute("SELECT COUNT(*) FROM morphemes").fetchone()[0]
    new_count = conn.execute("SELECT COUNT(*) FROM morphemes_clean").fetchone()[0]
    assert old_count == new_count, f"Row count mismatch: {old_count} vs {new_count}"

    conn.execute("DROP TABLE morphemes")
    conn.execute("ALTER TABLE morphemes_clean RENAME TO morphemes")

    # Recreate indexes
    conn.execute("CREATE INDEX idx_morphemes_word ON morphemes(word_id)")
    conn.execute("CREATE INDEX idx_morphemes_library ON morphemes(library_id)")

    conn.commit()
    print(f"  Morphemes table rebuilt: {new_count} rows, 3 columns")

    # =========================================
    # Verification
    # =========================================
    print("\n=== Verification ===")

    lib_count = conn.execute("SELECT COUNT(*) FROM morpheme_library").fetchone()[0]
    atom_count = conn.execute("SELECT COUNT(*) FROM morpheme_atoms").fetchone()[0]
    morph_count = conn.execute("SELECT COUNT(*) FROM morphemes").fetchone()[0]

    print(f"  morpheme_library: {lib_count} entries")
    print(f"  morpheme_atoms: {atom_count} atoms")
    print(f"  morphemes: {morph_count} instances")
    print(f"  Dedup ratio: {morph_count / lib_count:.1f}x")

    # Check features populated
    has_features = conn.execute(
        "SELECT COUNT(*) FROM morpheme_library WHERE pos_id IS NOT NULL"
    ).fetchone()[0]
    print(f"  Library entries with pos_id: {has_features}/{lib_count}")

    # Verify text reconstruction for verse 1:1
    print("\n  Verse 1:1 reconstruction:")
    words_11 = conn.execute(
        "SELECT id, text, word_index FROM words WHERE verse_surah=1 AND verse_ayah=1 ORDER BY word_index"
    ).fetchall()
    for w in words_11:
        morphs = conn.execute(
            "SELECT ml.uthmani_text FROM morphemes m "
            "JOIN morpheme_library ml ON m.library_id = ml.id "
            "WHERE m.word_id = ? ORDER BY m.id",
            (w['id'],)
        ).fetchall()
        reconstructed = "".join(m['uthmani_text'] or '' for m in morphs)
        match = "OK" if reconstructed == w['text'] else f"DIFF (got {reconstructed!r})"
        print(f"    [{w['word_index']}] {w['text']} -> {match}")

    # Check no orphan morphemes
    orphan_morphs = conn.execute("""
        SELECT COUNT(*) FROM morphemes m
        LEFT JOIN morpheme_library ml ON m.library_id = ml.id
        WHERE ml.id IS NULL
    """).fetchone()[0]
    print(f"  Orphan morphemes (no library entry): {orphan_morphs}")

    # Check library sharing
    shared = conn.execute("""
        SELECT library_id, COUNT(*) as cnt FROM morphemes
        GROUP BY library_id ORDER BY cnt DESC LIMIT 5
    """).fetchall()
    print(f"  Top shared library entries:")
    for s in shared:
        lib_text = conn.execute(
            "SELECT uthmani_text FROM morpheme_library WHERE id=?", (s['library_id'],)
        ).fetchone()
        text = lib_text['uthmani_text'] if lib_text else '?'
        print(f"    lib[{s['library_id']}] used {s['cnt']}x: {text!r}")

    elapsed = time.time() - t0
    print(f"\nMigration complete in {elapsed:.1f}s")

    return stats


def main():
    dry_run = "--dry-run" in sys.argv

    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        sys.exit(1)

    if not BACKUP_PATH.exists():
        print(f"Backup not found: {BACKUP_PATH}")
        print("Need data/kalima.db.backup-pre-uthmani with original feature data")
        sys.exit(1)

    # Safety backup
    if not dry_run:
        print(f"Creating safety backup: {SAFETY_BACKUP.name}")
        shutil.copy2(DB_PATH, SAFETY_BACKUP)

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute("PRAGMA journal_mode = WAL")

    backup_conn = sqlite3.connect(str(BACKUP_PATH))
    backup_conn.row_factory = sqlite3.Row

    print(f"{'DRY RUN — ' if dry_run else ''}Fix morpheme_library")
    print(f"Database: {DB_PATH}")
    print(f"Backup source: {BACKUP_PATH}")

    stats = migrate(conn, backup_conn, dry_run=dry_run)

    print(f"\n--- Summary ---")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    if not dry_run:
        print("\nRunning VACUUM...")
        conn.execute("VACUUM")
        print("Done.")

    backup_conn.close()
    conn.close()


if __name__ == "__main__":
    main()
