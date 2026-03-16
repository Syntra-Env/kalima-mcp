"""Location and verse text helpers.

Clarified naming:
- word_types: Unique word forms.
- word_instances: Specific occurrences.
- morpheme_types: Unique morpheme forms.
"""

import sqlite3
from typing import Optional, List, Dict


# --- Unified Anchoring Helpers ---

def get_entry_anchor(conn: sqlite3.Connection, entry_id: str) -> Optional[dict]:
    """Get anchor info for an entry."""
    row = conn.execute(
        "SELECT anchor_type, anchor_ids, verification, notes FROM holonomic_entries WHERE address = ?",
        (entry_id,)
    ).fetchone()
    return dict(row) if row else None


def entries_at_verse(conn: sqlite3.Connection, surah: int, ayah: int) -> list[str]:
    """Find entries anchored to this specific verse."""
    pattern = f"{surah}:{ayah}%"
    rows = conn.execute(
        "SELECT address FROM holonomic_entries WHERE anchor_type = 'word_instance' AND anchor_ids LIKE ?",
        (pattern,),
    ).fetchall()
    return [r['address'] for r in rows]


def entries_at_surah(conn: sqlite3.Connection, surah: int) -> list[str]:
    """Find all entry_ids that have any location in this surah."""
    pattern = f"{surah}:%"
    rows = conn.execute(
        "SELECT address FROM holonomic_entries WHERE (anchor_type = 'word_instance' AND anchor_ids LIKE ?) OR (anchor_type = 'surah' AND anchor_ids = ?)",
        (pattern, str(surah)),
    ).fetchall()
    return [r['address'] for r in rows]


# --- Word text composition (Atomic) ---

def compose_word_text(conn: sqlite3.Connection, word_type_id: int) -> str:
    """Reconstruct text for a unique word type from its atoms."""
    rows = conn.execute(
        """SELECT ma.base_letter, ma.diacritics
           FROM word_type_morphemes wtm
           JOIN morpheme_types mt ON wtm.morpheme_type_id = mt.id
           JOIN morpheme_atoms ma ON ma.morpheme_type_id = mt.id
           WHERE wtm.word_type_id = ?
           ORDER BY wtm.position, ma.position""",
        (word_type_id,),
    ).fetchall()
    return ''.join((r['base_letter'] or '') + (r['diacritics'] or '') for r in rows)


def compose_verse_text(conn: sqlite3.Connection, surah: int, ayah: int) -> Optional[str]:
    """Reconstruct verse text from word instances."""
    rows = conn.execute(
        """SELECT wi.word_index, wtm.position, ma.base_letter, ma.diacritics
           FROM word_instances wi
           JOIN word_type_morphemes wtm ON wi.word_type_id = wtm.word_type_id
           JOIN morpheme_types mt ON wtm.morpheme_type_id = mt.id
           JOIN morpheme_atoms ma ON ma.morpheme_type_id = mt.id
           WHERE wi.verse_surah = ? AND wi.verse_ayah = ?
           ORDER BY wi.word_index, wtm.position, ma.position""",
        (surah, ayah),
    ).fetchall()

    if not rows: return None

    word_map = {}
    for r in rows:
        word_map.setdefault(r['word_index'], []).append((r['base_letter'] or '') + (r['diacritics'] or ''))

    return ' '.join(''.join(parts) for _, parts in sorted(word_map.items()))


def batch_compose_verse_texts(conn: sqlite3.Connection, verse_keys: List[tuple]) -> Dict[tuple, str]:
    """Reconstruct multiple verse texts."""
    results = {}
    for s, a in verse_keys:
        text = compose_verse_text(conn, s, a)
        if text: results[(s, a)] = text
    return results


def compose_surah_texts(conn: sqlite3.Connection, surah: int) -> list[dict]:
    """Get all verses for a surah."""
    rows = conn.execute(
        "SELECT DISTINCT verse_ayah FROM word_instances WHERE verse_surah = ? ORDER BY verse_ayah",
        (surah,),
    ).fetchall()

    verses = []
    for r in rows:
        ayah = r['verse_ayah']
        verses.append({
            "ayah_number": ayah,
            "text": compose_verse_text(conn, surah, ayah)
        })
    return verses


def verse_exists(conn: sqlite3.Connection, surah: int, ayah: int) -> bool:
    """Check if a verse exists."""
    row = conn.execute(
        "SELECT 1 FROM word_instances WHERE verse_surah = ? AND verse_ayah = ? LIMIT 1",
        (surah, ayah),
    ).fetchone()
    return row is not None
