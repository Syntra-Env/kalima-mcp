"""Quran text tools: verse retrieval, surah listing, and search."""

from mcp.server.fastmcp import FastMCP

from ..db import get_connection
from ..utils.arabic import normalize_arabic

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
        row = conn.execute(
            """SELECT v.surah_number, v.ayah_number, vt.text
               FROM verses v
               JOIN verse_texts vt ON v.surah_number = vt.surah_number AND v.ayah_number = vt.ayah_number
               WHERE v.surah_number = ? AND v.ayah_number = ?""",
            (surah, ayah)
        ).fetchone()
        if not row:
            return {"error": f"Verse {surah}:{ayah} not found"}
        return dict(row)

    @mcp.tool()
    def get_surah(surah: int) -> dict:
        """Retrieve an entire surah (chapter) with all its verses."""
        conn = get_connection()
        surah_row = conn.execute(
            "SELECT number, name FROM surahs WHERE number = ?",
            (surah,)
        ).fetchone()
        if not surah_row:
            return {"error": f"Surah {surah} not found"}

        verses = conn.execute(
            """SELECT v.surah_number, v.ayah_number, vt.text
               FROM verses v
               JOIN verse_texts vt ON v.surah_number = vt.surah_number AND v.ayah_number = vt.ayah_number
               WHERE v.surah_number = ?
               ORDER BY v.ayah_number ASC""",
            (surah,)
        ).fetchall()

        return {
            "surah": dict(surah_row),
            "verses": [dict(v) for v in verses]
        }

    @mcp.tool()
    def list_surahs() -> list[dict]:
        """Get a list of all 114 surahs with their Arabic names and verse counts."""
        conn = get_connection()
        rows = conn.execute(
            "SELECT number, name FROM surahs ORDER BY number ASC"
        ).fetchall()
        return [dict(r) for r in rows]

    @mcp.tool()
    def search_verses(query: str, limit: int = 20) -> list[dict]:
        """Search for verses containing specific Arabic text.

        Uses normalized text matching (diacritics removed, alef/yaa forms normalized).
        """
        conn = get_connection()
        normalized_query = normalize_arabic(query)
        rows = conn.execute(
            """SELECT surah_number, ayah_number, text
               FROM verse_texts
               WHERE normalized_text LIKE ?
               ORDER BY surah_number ASC, ayah_number ASC
               LIMIT ?""",
            (f"%{normalized_query}%", limit)
        ).fetchall()
        return [dict(r) for r in rows]
