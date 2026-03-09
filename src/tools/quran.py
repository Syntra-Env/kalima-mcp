"""Quran text tools: verse retrieval, surah listing, and search."""

from mcp.server.fastmcp import FastMCP

from ..db import get_connection
from ..utils.arabic import normalize_arabic
from ..utils.surahs import get_surah_name, list_all_surahs
from ..utils.units import compose_verse_text, compose_surah_texts

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
        rows = conn.execute(
            """SELECT verse_surah AS surah_number, verse_ayah AS ayah_number,
                      GROUP_CONCAT(text, ' ') AS text
               FROM (SELECT verse_surah, verse_ayah, text, normalized_text FROM words
                     ORDER BY verse_surah, verse_ayah, word_index)
               GROUP BY verse_surah, verse_ayah
               HAVING GROUP_CONCAT(normalized_text, ' ') LIKE ?
               ORDER BY verse_surah ASC, verse_ayah ASC
               LIMIT ?""",
            (f"%{normalized_query}%", limit)
        ).fetchall()
        return [dict(r) for r in rows]
