"""Quran text tools: verse retrieval, surah listing, and search."""

from mcp.server.fastmcp import FastMCP

from ..db import get_connection
from ..utils.arabic import normalize_arabic
from ..utils.surahs import get_surah_name, list_all_surahs
from ..utils.units import compose_verse_text, compose_surah_texts, compose_word_text

mcp: FastMCP


def register(server: FastMCP):
    global mcp
    mcp = server

    @mcp.tool()
    def get_verse(surah: int, ayah: int) -> dict:
        """Retrieve a specific verse."""
        conn = get_connection()
        text = compose_verse_text(conn, surah, ayah)
        if text is None: return {"error": "Verse not found"}
        return {"surah": surah, "ayah": ayah, "text": text}

    @mcp.tool()
    def get_surah(surah: int) -> dict:
        """Retrieve an entire surah."""
        conn = get_connection()
        name = get_surah_name(surah)
        if not name: return {"error": "Surah not found"}
        return {"surah": {"number": surah, "name": name}, "verses": compose_surah_texts(conn, surah)}

    @mcp.tool()
    def list_surahs() -> list[dict]:
        """List all surahs."""
        return list_all_surahs()

    @mcp.tool()
    def search_verses(query: str | None = None, root: str | None = None, limit: int = 20) -> list[dict]:
        """Search for verses by text or root."""
        conn = get_connection()
        from .linguistic import _resolve_feature_id, _normalize_feature
        from ..utils.units import batch_compose_verse_texts

        candidate_keys = None
        if root:
            rid = _resolve_feature_id(conn, "root", _normalize_feature("root", root))
            if rid:
                rows = conn.execute(
                    """SELECT DISTINCT wi.verse_surah, wi.verse_ayah 
                       FROM word_instances wi
                       JOIN word_type_morphemes wtm ON wi.word_type_id = wtm.word_type_id
                       JOIN morpheme_types mt ON wtm.morpheme_type_id = mt.id
                       WHERE mt.root_id = ?""", (rid,)
                ).fetchall()
                candidate_keys = {(r[0], r[1]) for r in rows}
            else: return []

        if candidate_keys is None:
            rows = conn.execute("SELECT DISTINCT verse_surah, verse_ayah FROM word_instances").fetchall()
            candidate_keys = {(r[0], r[1]) for r in rows}

        results = []
        norm_query = normalize_arabic(query) if query else None
        sorted_keys = sorted(list(candidate_keys))
        
        # Process in chunks
        chunk_size = 500
        for i in range(0, len(sorted_keys), chunk_size):
            chunk = sorted_keys[i:i+chunk_size]
            v_map = batch_compose_verse_texts(conn, chunk)
            for (s, a), text in v_map.items():
                if not norm_query or norm_query in normalize_arabic(text):
                    results.append({"ref": f"{s}:{a}", "text": text})
                    if len(results) >= limit: return results
        return results

    @mcp.tool()
    def search_expressions(surah: int, ayah: int, word_start: int, word_end: int) -> list[dict]:
        """Find other occurrences of the same word-type sequence."""
        conn = get_connection()
        target_rows = conn.execute(
            "SELECT word_type_id FROM word_instances WHERE verse_surah=? AND verse_ayah=? AND word_index BETWEEN ? AND ? ORDER BY word_index",
            (surah, ayah, word_start, word_end)
        ).fetchall()
        if not target_rows: return {"error": "Expression not found"}
        
        target_ids = [r[0] for r in target_rows]
        n = len(target_ids)
        candidates = conn.execute("SELECT verse_surah, verse_ayah, word_index FROM word_instances WHERE word_type_id=?", (target_ids[0],)).fetchall()
        
        matches = []
        for c in candidates:
            if c[0] == surah and c[1] == ayah and c[2] == word_start: continue
            is_match = True
            for i in range(1, n):
                nxt = conn.execute("SELECT word_type_id FROM word_instances WHERE verse_surah=? AND verse_ayah=? AND word_index=?", (c[0], c[1], c[2]+i)).fetchone()
                if not nxt or nxt[0] != target_ids[i]:
                    is_match = False; break
            if is_match:
                matches.append({"surah": c[0], "ayah": c[1], "range": f"{c[2]}-{c[2]+n-1}", "text": compose_verse_text(conn, c[0], c[1])})
        return matches
