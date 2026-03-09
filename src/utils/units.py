"""Location and verse text helpers.

Provides:
- entry_locations read/write helpers (many-to-many entry-to-Quranic-location)
- Verse text composition through the compositional chain:
  words → word_library → word_morphemes → morpheme_library.uthmani_text
"""

import sqlite3
from typing import Optional


# --- Entry location helpers ---

def get_entry_locations(conn: sqlite3.Connection, entry_id: str) -> list[dict]:
    """Get all locations for an entry from entry_locations."""
    rows = conn.execute(
        """SELECT surah, ayah_start, ayah_end, word_start, word_end
           FROM entry_locations WHERE entry_id = ?""",
        (entry_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def add_entry_location(
    conn: sqlite3.Connection,
    entry_id: str,
    surah: int,
    ayah_start: Optional[int] = None,
    ayah_end: Optional[int] = None,
    word_start: Optional[int] = None,
    word_end: Optional[int] = None,
) -> None:
    """Add a location to an entry. Idempotent (ignores duplicates)."""
    conn.execute(
        """INSERT OR IGNORE INTO entry_locations
           (entry_id, surah, ayah_start, ayah_end, word_start, word_end)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (entry_id, surah, ayah_start, ayah_end, word_start, word_end),
    )


def entries_at_verse(conn: sqlite3.Connection, surah: int, ayah: int) -> list[str]:
    """Find entry_ids that cover a specific verse (exact, range, or surah-level)."""
    rows = conn.execute(
        """SELECT DISTINCT entry_id FROM entry_locations
           WHERE surah = ?
             AND (ayah_start IS NULL
                  OR ayah_start = ?
                  OR (ayah_end IS NOT NULL AND ? BETWEEN ayah_start AND ayah_end))""",
        (surah, ayah, ayah),
    ).fetchall()
    return [r['entry_id'] for r in rows]


def entries_at_surah(conn: sqlite3.Connection, surah: int) -> list[str]:
    """Find all entry_ids that have any location in this surah."""
    rows = conn.execute(
        "SELECT DISTINCT entry_id FROM entry_locations WHERE surah = ?",
        (surah,),
    ).fetchall()
    return [r['entry_id'] for r in rows]


# --- Verse text composition (compositional chain) ---

def compose_verse_text(conn: sqlite3.Connection, surah: int, ayah: int) -> Optional[str]:
    """Compose verse text through: words → word_library → word_morphemes → morpheme_library."""
    rows = conn.execute(
        """SELECT w.word_index, wm.position, ml.uthmani_text
           FROM words w
           JOIN word_morphemes wm ON wm.word_library_id = w.word_library_id
           JOIN morpheme_library ml ON wm.morpheme_library_id = ml.id
           WHERE w.verse_surah = ? AND w.verse_ayah = ?
           ORDER BY w.word_index, wm.position""",
        (surah, ayah),
    ).fetchall()
    if not rows:
        return None
    words: dict[int, list[str]] = {}
    for r in rows:
        words.setdefault(r['word_index'], []).append(r['uthmani_text'] or '')
    return ' '.join(''.join(parts) for _, parts in sorted(words.items()))


def compose_surah_texts(conn: sqlite3.Connection, surah: int) -> list[dict]:
    """Compose all verse texts for a surah. Returns list of {surah_number, ayah_number, text}."""
    rows = conn.execute(
        """SELECT w.verse_ayah, w.word_index, wm.position, ml.uthmani_text
           FROM words w
           JOIN word_morphemes wm ON wm.word_library_id = w.word_library_id
           JOIN morpheme_library ml ON wm.morpheme_library_id = ml.id
           WHERE w.verse_surah = ?
           ORDER BY w.verse_ayah, w.word_index, wm.position""",
        (surah,),
    ).fetchall()
    # Group by ayah -> word_index -> morpheme parts
    verses: dict[int, dict[int, list[str]]] = {}
    for r in rows:
        verse_words = verses.setdefault(r['verse_ayah'], {})
        verse_words.setdefault(r['word_index'], []).append(r['uthmani_text'] or '')
    return [
        {
            "surah_number": surah,
            "ayah_number": ayah,
            "text": ' '.join(''.join(parts) for _, parts in sorted(word_map.items())),
        }
        for ayah, word_map in sorted(verses.items())
    ]


def verse_exists(conn: sqlite3.Connection, surah: int, ayah: int) -> bool:
    """Check if a verse exists (has words)."""
    row = conn.execute(
        "SELECT 1 FROM words WHERE verse_surah = ? AND verse_ayah = ? LIMIT 1",
        (surah, ayah),
    ).fetchone()
    return row is not None


def batch_compose_verse_texts(
    conn: sqlite3.Connection, verse_keys: list[tuple[int, int]]
) -> dict[tuple[int, int], str]:
    """Compose verse texts for multiple (surah, ayah) pairs in a single query."""
    if not verse_keys:
        return {}
    placeholders = ','.join(f'({s},{a})' for s, a in verse_keys)
    rows = conn.execute(
        f"""SELECT w.verse_surah, w.verse_ayah, w.word_index, wm.position, ml.uthmani_text
            FROM words w
            JOIN word_morphemes wm ON wm.word_library_id = w.word_library_id
            JOIN morpheme_library ml ON wm.morpheme_library_id = ml.id
            WHERE (w.verse_surah, w.verse_ayah) IN ({placeholders})
            ORDER BY w.verse_surah, w.verse_ayah, w.word_index, wm.position"""
    ).fetchall()
    # Group by (surah, ayah) -> word_index -> morpheme parts
    verses: dict[tuple[int, int], dict[int, list[str]]] = {}
    for r in rows:
        key = (r['verse_surah'], r['verse_ayah'])
        word_map = verses.setdefault(key, {})
        word_map.setdefault(r['word_index'], []).append(r['uthmani_text'] or '')
    return {
        key: ' '.join(''.join(parts) for _, parts in sorted(word_map.items()))
        for key, word_map in verses.items()
    }


def compose_word_text(conn: sqlite3.Connection, word_library_id: int) -> str:
    """Compose a single word's text from its morpheme library entries."""
    rows = conn.execute(
        """SELECT ml.uthmani_text
           FROM word_morphemes wm
           JOIN morpheme_library ml ON wm.morpheme_library_id = ml.id
           WHERE wm.word_library_id = ?
           ORDER BY wm.position""",
        (word_library_id,),
    ).fetchall()
    return ''.join(r['uthmani_text'] or '' for r in rows)
