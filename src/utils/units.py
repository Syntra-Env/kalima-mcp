"""Location and verse text helpers.

Schema clarification:
- word_types: Only contains id (dummy table)
- word_instances: Points to morpheme_types.id via word_type_id
- morpheme_types: Contains full word text in uthmani_text field
- word_type_morphemes: Legacy table with incorrect mappings (unused)
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
    """Get text for a word type from morpheme_types.
    
    Note: word_type_id in this schema is actually morpheme_type.id,
    which stores the full word text in uthmani_text.
    """
    row = conn.execute(
        "SELECT uthmani_text FROM morpheme_types WHERE id = ?",
        (word_type_id,),
    ).fetchone()
    return row['uthmani_text'] if row else ''


def compose_verse_text(conn: sqlite3.Connection, surah: int, ayah: int) -> Optional[str]:
    """Reconstruct verse text from word_instances via morpheme_types.
    
    word_type_id in word_instances points to morpheme_types.id,
    which has the correct uthmani_text for each word.
    """
    words = conn.execute(
        """SELECT mt.uthmani_text
           FROM word_instances wi
           JOIN morpheme_types mt ON wi.word_type_id = mt.id
           WHERE wi.verse_surah = ? AND wi.verse_ayah = ?
           ORDER BY wi.word_index""",
        (surah, ayah),
    ).fetchall()
    
    if not words:
        return None
    
    return ' '.join(w['uthmani_text'] for w in words)


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
