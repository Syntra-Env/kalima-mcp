"""Location and verse text helpers.

Provides:
- entry_locations read/write helpers (many-to-many entry-to-Quranic-location)
- Verse text composition from the words table
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


# --- Verse text composition (uses words table, not units) ---

def compose_verse_text(conn: sqlite3.Connection, surah: int, ayah: int) -> Optional[str]:
    """Compose verse text from words. Returns None if verse not found."""
    rows = conn.execute(
        "SELECT text FROM words WHERE verse_surah = ? AND verse_ayah = ? ORDER BY word_index",
        (surah, ayah),
    ).fetchall()
    if not rows:
        return None
    return ' '.join(r['text'] for r in rows)


def compose_surah_texts(conn: sqlite3.Connection, surah: int) -> list[dict]:
    """Compose all verse texts for a surah. Returns list of {surah_number, ayah_number, text}."""
    rows = conn.execute(
        "SELECT verse_surah, verse_ayah, text FROM words WHERE verse_surah = ? ORDER BY verse_ayah, word_index",
        (surah,),
    ).fetchall()
    verses: dict[int, list[str]] = {}
    for r in rows:
        verses.setdefault(r['verse_ayah'], []).append(r['text'])
    return [
        {"surah_number": surah, "ayah_number": ayah, "text": ' '.join(texts)}
        for ayah, texts in sorted(verses.items())
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
        f"""SELECT verse_surah, verse_ayah, GROUP_CONCAT(text, ' ') AS text
            FROM (SELECT verse_surah, verse_ayah, text FROM words
                  WHERE (verse_surah, verse_ayah) IN ({placeholders})
                  ORDER BY verse_surah, verse_ayah, word_index)
            GROUP BY verse_surah, verse_ayah"""
    ).fetchall()
    return {(r['verse_surah'], r['verse_ayah']): r['text'] for r in rows}
