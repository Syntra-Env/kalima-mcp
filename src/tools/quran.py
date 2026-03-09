"""Quran text tools: verse retrieval, surah listing, and search."""

from mcp.server.fastmcp import FastMCP

from ..db import get_connection
from ..utils.arabic import normalize_arabic
from ..utils.surahs import get_surah_name, list_all_surahs
from ..utils.units import compose_verse_text, compose_surah_texts, compose_word_text

mcp: FastMCP  # injected by server.py


def register(server: FastMCP):
    global mcp
    mcp = server

    @mcp.tool()
    def get_verse(surah: int, ayah: int) -> dict:
        """Retrieve a specific verse from the Quran with ONLY its Arabic text.

        DO NOT add English translations when presenting verses to the user.
        Only show interpretations if they exist in the database.
        """
        conn = get_connection()
        text = compose_verse_text(conn, surah, ayah)
        if text is None:
            return {"error": f"Verse {surah}:{ayah} not found"}
        return {"surah_number": surah, "ayah_number": ayah, "text": text}

    @mcp.tool()
    def get_surah(surah: int) -> dict:
        """Retrieve an entire surah (chapter) with all its verses."""
        conn = get_connection()
        name = get_surah_name(surah)
        if not name:
            return {"error": f"Surah {surah} not found"}

        verses = compose_surah_texts(conn, surah)

        return {
            "surah": {"number": surah, "name": name},
            "verses": verses
        }

    @mcp.tool()
    def list_surahs() -> list[dict]:
        """Get a list of all 114 surahs with their Arabic names and verse counts."""
        return list_all_surahs()

    @mcp.tool()
    def search_verses(query: str, limit: int = 20) -> list[dict]:
        """Search for verses containing specific Arabic text.

        Uses normalized text matching (diacritics removed, alef/yaa forms normalized).
        """
        conn = get_connection()
        normalized_query = normalize_arabic(query)

        # Compose all verse texts through the compositional chain
        rows = conn.execute(
            """SELECT w.verse_surah, w.verse_ayah, w.word_index,
                      wm.position, ml.uthmani_text
               FROM words w
               JOIN word_morphemes wm ON wm.word_library_id = w.word_library_id
               JOIN morpheme_library ml ON wm.morpheme_library_id = ml.id
               ORDER BY w.verse_surah, w.verse_ayah, w.word_index, wm.position"""
        ).fetchall()

        # Group: (surah, ayah) -> word_index -> [morpheme parts]
        verses: dict[tuple[int, int], dict[int, list[str]]] = {}
        for r in rows:
            key = (r['verse_surah'], r['verse_ayah'])
            word_map = verses.setdefault(key, {})
            word_map.setdefault(r['word_index'], []).append(r['uthmani_text'] or '')

        results = []
        for (surah, ayah), word_map in sorted(verses.items()):
            text = ' '.join(''.join(parts) for _, parts in sorted(word_map.items()))
            if normalized_query in normalize_arabic(text):
                results.append({"surah_number": surah, "ayah_number": ayah, "text": text})
                if len(results) >= limit:
                    break
        return results
