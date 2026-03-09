"""Migrate morpheme forms to include full Uthmani orthography.

Adds `uthmani_form` column to morphemes and populates it by aligning
the Uthmani word text (from words.text) with the simplified morpheme forms.

This preserves ALL diacritics, tajweed marks, tatweel, superscript alef,
maddah, and other Uthmani-specific characters that morpheme.form currently strips.
"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"

# Known single-char substitutions: Uthmani char -> morpheme char
SUBSTITUTIONS = {
    "\u0671": "\u0627",  # Alef wasla -> plain alef
    "\u06E7": "\u06E6",  # Small high yeh -> small yeh (e.g. Ibrahim)
}

# Multi-char substitutions: sequence in Uthmani -> sequence in morpheme form.
# The Uthmani text uses tatweel + hamza-above + alef for hamza-seat-on-alef,
# while morpheme forms use standalone hamza + alef.
# Pattern: ـَٔ (tatweel + fatha + hamza-above) -> ء (standalone hamza)
# But fatha may or may not be present, so we handle the core: ـٔ -> ء
# and also ـ + small-high-yeh -> small-yeh
MULTI_SUBSTITUTIONS = [
    # (uthmani_sequence, form_sequence)
    # Hamza on tatweel: ـٔ (tatweel + combining hamza above) -> ء (standalone hamza)
    ("\u0640\u0654", "\u0621"),
]


def chars_match(uthmani_ch: str, form_ch: str) -> bool:
    """Check if an Uthmani character matches a morpheme form character,
    accounting for known substitutions."""
    if uthmani_ch == form_ch:
        return True
    return SUBSTITUTIONS.get(uthmani_ch) == form_ch


def align_uthmani_to_morphemes(word_text: str, morpheme_forms: list[str]) -> list[str] | None:
    """Split Uthmani word text into segments aligned with morpheme forms.

    Strategy: walk through word_text char by char. Try to match against the
    current position in the concatenated morpheme forms. If it matches, consume
    both. If it doesn't match, treat the word_text character as an Uthmani extra
    (diacritic, tajweed mark, tatweel, etc.) and attach it to the current segment.

    This avoids pre-classifying characters — the morpheme forms themselves define
    what's "base" and what's "extra" by their presence or absence.

    Returns a list of Uthmani segments (one per morpheme) or None if alignment fails.
    """
    if not morpheme_forms:
        return None

    concat = "".join(morpheme_forms)

    # Fast path: no difference
    if word_text == concat:
        return list(morpheme_forms)

    # Build morpheme boundary positions in the concatenated form
    boundaries = []
    pos = 0
    for form in morpheme_forms:
        boundaries.append((pos, pos + len(form)))
        pos += len(form)

    # Align: walk through word_text, consuming form characters
    form_idx = 0
    alignments: list[int] = []  # parallel to word_text chars

    i = 0
    while i < len(word_text):
        ch = word_text[i]

        # Try multi-char substitutions first
        multi_matched = False
        for uth_seq, form_seq in MULTI_SUBSTITUTIONS:
            if word_text[i:i+len(uth_seq)] == uth_seq:
                # Check if form_seq matches at current form position
                if concat[form_idx:form_idx+len(form_seq)] == form_seq:
                    # All chars in the Uthmani sequence align to the form sequence
                    for j in range(len(uth_seq)):
                        alignments.append(form_idx)
                    form_idx += len(form_seq)
                    i += len(uth_seq)
                    multi_matched = True
                    break
                else:
                    # The Uthmani sequence is present but form doesn't have the substitution
                    # Treat the tatweel as extra, continue with next char
                    pass

        if multi_matched:
            continue

        if form_idx < len(concat) and chars_match(ch, concat[form_idx]):
            # Matches current form character — consume it
            alignments.append(form_idx)
            form_idx += 1
        else:
            # Extra character in Uthmani — attach to current position
            # Use form_idx if still in range, otherwise last position
            attachpoint = form_idx if form_idx < len(concat) else len(concat) - 1
            alignments.append(attachpoint)

        i += 1

    # Check we consumed all form characters.
    # Exception: trailing morphemes whose form is just tatweel (U+0640) are
    # placeholder markers for grammatical features expressed through diacritics.
    # They have no textual realization in the word — skip them.
    if form_idx != len(concat):
        remaining = concat[form_idx:]
        if remaining.replace("\u0640", "") == "":
            # All remaining form chars are tatweels — acceptable
            pass
        else:
            return None

    # Now split word_text into segments based on morpheme boundaries.
    # For trailing tatweel morphemes that had no matching chars in the word,
    # any extras attached to their form_idx range still get captured.
    # Also handle the case where extras point beyond the last consumed position
    # by assigning them to the last morpheme.
    segments = []
    for mi, (start, end) in enumerate(boundaries):
        segment_chars = []
        is_last = (mi == len(boundaries) - 1)
        for j, ch in enumerate(word_text):
            a = alignments[j]
            if start <= a < end:
                segment_chars.append(ch)
            elif is_last and a >= end:
                # Trailing extras beyond the last boundary — attach to last morpheme
                segment_chars.append(ch)
        segments.append("".join(segment_chars))

    return segments


def migrate(conn: sqlite3.Connection, dry_run: bool = False) -> dict:
    """Run the migration. Returns stats."""
    # Add column if not exists
    try:
        conn.execute("ALTER TABLE morphemes ADD COLUMN uthmani_form TEXT")
        conn.commit()
        print("Added uthmani_form column to morphemes.")
    except sqlite3.OperationalError:
        print("uthmani_form column already exists.")

    # Get all words with their morphemes
    words = conn.execute("""
        SELECT w.id, w.text, w.verse_surah, w.verse_ayah, w.word_index
        FROM words w
        ORDER BY w.verse_surah, w.verse_ayah, w.word_index
    """).fetchall()

    stats = {"total_words": 0, "perfect": 0, "aligned": 0, "failed": 0, "failures": []}

    for word in words:
        stats["total_words"] += 1
        word_id = word["id"]
        word_text = word["text"]

        morphemes = conn.execute("""
            SELECT id, form FROM morphemes
            WHERE word_id = ?
            ORDER BY id
        """, (word_id,)).fetchall()

        forms = [m["form"] for m in morphemes]
        mor_ids = [m["id"] for m in morphemes]

        # Try alignment
        concat = "".join(forms)
        if word_text == concat:
            # Perfect match — uthmani_form = form
            stats["perfect"] += 1
            if not dry_run:
                for mid, form in zip(mor_ids, forms):
                    conn.execute(
                        "UPDATE morphemes SET uthmani_form = ? WHERE id = ?",
                        (form, mid)
                    )
        else:
            segments = align_uthmani_to_morphemes(word_text, forms)
            if segments is not None:
                # Verify reconstruction
                reconstructed = "".join(segments)
                if reconstructed == word_text:
                    stats["aligned"] += 1
                    if not dry_run:
                        for mid, segment in zip(mor_ids, segments):
                            conn.execute(
                                "UPDATE morphemes SET uthmani_form = ? WHERE id = ?",
                                (segment, mid)
                            )
                else:
                    stats["failed"] += 1
                    stats["failures"].append({
                        "word_id": word_id,
                        "location": f"{word['verse_surah']}:{word['verse_ayah']}:{word['word_index']}",
                        "word_text": word_text,
                        "forms": forms,
                        "segments": segments,
                        "reconstructed": reconstructed,
                        "reason": "reconstruction_mismatch",
                    })
                    # Fallback: use existing form as uthmani_form
                    if not dry_run:
                        for mid, form in zip(mor_ids, forms):
                            conn.execute(
                                "UPDATE morphemes SET uthmani_form = ? WHERE id = ?",
                                (form, mid)
                            )
            else:
                stats["failed"] += 1
                stats["failures"].append({
                    "word_id": word_id,
                    "location": f"{word['verse_surah']}:{word['verse_ayah']}:{word['word_index']}",
                    "word_text": word_text,
                    "forms": forms,
                    "reason": "alignment_failed",
                })
                # Fallback: use existing form as uthmani_form (no enrichment, no data loss)
                if not dry_run:
                    for mid, form in zip(mor_ids, forms):
                        conn.execute(
                            "UPDATE morphemes SET uthmani_form = ? WHERE id = ?",
                            (form, mid)
                        )

    if not dry_run:
        conn.commit()

    return stats


def main():
    dry_run = "--dry-run" in sys.argv

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")

    print(f"{'DRY RUN — ' if dry_run else ''}Migrating morpheme Uthmani forms...")
    print(f"Database: {DB_PATH}")
    print()

    stats = migrate(conn, dry_run=dry_run)

    print(f"Total words:    {stats['total_words']}")
    print(f"Perfect match:  {stats['perfect']}")
    print(f"Aligned:        {stats['aligned']}")
    print(f"Failed:         {stats['failed']}")
    print()

    if stats["failures"]:
        # Write failures to file (avoid encoding issues on Windows console)
        fail_path = DB_PATH.parent / "uthmani_failures.txt"
        with open(fail_path, "w", encoding="utf-8") as fp:
            for f in stats["failures"]:
                fp.write(f"{f['location']} word={f['word_text']} forms={f['forms']} reason={f['reason']}\n")
                if f.get("segments"):
                    fp.write(f"  segments={f['segments']} reconstructed={f.get('reconstructed', '?')}\n")
        print(f"Failures written to {fail_path}")

    if not dry_run:
        # Verify: count morphemes with uthmani_form set
        filled = conn.execute("SELECT COUNT(*) FROM morphemes WHERE uthmani_form IS NOT NULL").fetchone()[0]
        total = conn.execute("SELECT COUNT(*) FROM morphemes").fetchone()[0]
        print(f"\nMorphemes with uthmani_form: {filled}/{total}")

    conn.close()


if __name__ == "__main__":
    main()
