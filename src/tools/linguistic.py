"""Linguistic analysis tools: morphological search, evidence, term linking.

Clarified naming:
- word_types: Unique word forms (DNA).
- word_instances: Specific occurrences.
"""

from mcp.server.fastmcp import FastMCP

from ..db import get_connection
from ..utils.features import TERM_TYPE_TO_FEATURE
from ..utils.units import batch_compose_verse_texts, compose_word_text

mcp: FastMCP

# Map user-friendly names to database codes
_FEATURE_MAPPINGS: dict[str, dict[str, str]] = {
    "pos": {
        "verb": "V", "noun": "N", "adjective": "ADJ", "pronoun": "PRON",
        "preposition": "P", "particle": "T",
    },
    "aspect": {
        "imperfective": "IMPF", "present": "IMPF",
        "perfective": "PERF", "past": "PERF",
        "imperative": "IMPV",
    },
}


def _normalize_feature(key: str, value: str) -> str:
    if key == 'root': value = value.replace('-', '')
    return _FEATURE_MAPPINGS.get(key, {}).get(value.lower(), value)


def _resolve_feature_id(conn, feature_name: str, value: str) -> int | None:
    """Resolve a feature name + value to a features.id."""
    mapping = TERM_TYPE_TO_FEATURE.get(feature_name)
    if not mapping: return None
    ft, cat = mapping
    sql = "SELECT id FROM features WHERE feature_type = ? AND lookup_key = ?"
    params = [ft, value]
    if cat:
        sql += " AND category = ?"
        params.append(cat)
    else:
        sql += " AND category IS NULL"
    row = conn.execute(sql, params).fetchone()
    return row['id'] if row else None


def register(server: FastMCP):
    global mcp
    mcp = server

    @mcp.tool()
    def search_features(query: str, feature_type: str | None = None, limit: int = 50) -> list[dict]:
        """Search for linguistic features (roots, lemmas, etc) ignoring diacritics."""
        conn = get_connection()
        from ..utils.arabic import normalize_arabic
        norm_query = normalize_arabic(query)
        sql = "SELECT id, feature_type, lookup_key, label_ar, label_en, frequency FROM features WHERE lookup_key LIKE ?"
        params: list = [f"%{norm_query}%"]
        if feature_type:
            sql += " AND feature_type = ?"
            params.append(feature_type)
        sql += " ORDER BY frequency DESC LIMIT ?"
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    @mcp.tool()
    def search_word_types(text: str, limit: int = 50) -> list[dict]:
        """Search for unique word types by text."""
        conn = get_connection()
        from ..utils.arabic import normalize_arabic
        norm_query = normalize_arabic(text)
        # Use normalized_text column on word_instances for SQL-level filtering,
        # then map back to distinct word_types
        rows = conn.execute(
            """SELECT DISTINCT wi.word_type_id
               FROM word_instances wi
               WHERE wi.normalized_text LIKE ?
               LIMIT ?""",
            (f"%{norm_query}%", limit)
        ).fetchall()
        results = []
        for r in rows:
            w_text = compose_word_text(conn, r['word_type_id'])
            results.append({"word_type_id": r['word_type_id'], "text": w_text})
        return results

    @mcp.tool()
    def get_word_identity(surah: int, ayah: int, word_index: int) -> dict:
        """Get the full identity chain for a specific word instance."""
        conn = get_connection()
        row = conn.execute(
            """SELECT wi.id as instance_id, wi.word_type_id,
                      rf_lemma.id as lemma_id, rf_lemma.lookup_key as lemma,
                      rf_root.id as root_id, rf_root.lookup_key as root
               FROM word_instances wi
               JOIN word_type_morphemes wtm ON wi.word_type_id = wtm.word_type_id
               JOIN morpheme_types mt ON wtm.morpheme_type_id = mt.id
               LEFT JOIN features rf_lemma ON mt.lemma_id = rf_lemma.id
               LEFT JOIN features rf_root ON mt.root_id = rf_root.id
               WHERE wi.verse_surah = ? AND wi.verse_ayah = ? AND wi.word_index = ?
               ORDER BY rf_root.id DESC, rf_lemma.id DESC
               LIMIT 1""",
            (surah, ayah, word_index)
        ).fetchone()
        if not row: return {"error": "Word not found"}
        return {
            "instance_id": row['instance_id'],
            "word_type_id": row['word_type_id'],
            "lemma": {"id": row['lemma_id'], "value": row['lemma']},
            "root": {"id": row['root_id'], "value": row['root']},
            "text": compose_word_text(conn, row['word_type_id'])
        }

    @mcp.tool()
    def search_by_linguistic_features(
        pos: str | None = None,
        root: str | None = None,
        lemma: str | None = None,
        verb_form: str | None = None,
        surah: int | None = None,
        limit: int = 50,
    ) -> dict:
        """Search verses by linguistic features."""
        conn = get_connection()
        conditions = []
        params = []

        if root:
            rid = _resolve_feature_id(conn, "root", _normalize_feature("root", root))
            if rid: conditions.append("mt.root_id = ?"); params.append(rid)
        if lemma:
            lid = _resolve_feature_id(conn, "lemma", _normalize_feature("lemma", lemma))
            if lid: conditions.append("mt.lemma_id = ?"); params.append(lid)
        if pos:
            pid = _resolve_feature_id(conn, "pos", _normalize_feature("pos", pos))
            if pid: conditions.append("mt.pos_id = ?"); params.append(pid)
        if verb_form:
            vfid = _resolve_feature_id(conn, "verb_form", _normalize_feature("verb_form", verb_form))
            if vfid: conditions.append("mt.verb_form_id = ?"); params.append(vfid)

        if surah: conditions.append("wi.verse_surah = ?"); params.append(surah)
        if not conditions: return {"error": "Specify at least one feature"}

        where = " AND ".join(conditions)
        sql = f"""SELECT DISTINCT wi.verse_surah, wi.verse_ayah 
                  FROM word_instances wi
                  JOIN word_type_morphemes wtm ON wi.word_type_id = wtm.word_type_id
                  JOIN morpheme_types mt ON wtm.morpheme_type_id = mt.id
                  WHERE {where} ORDER BY wi.verse_surah, wi.verse_ayah LIMIT ?"""
        params.append(limit)
        rows = conn.execute(sql, params).fetchall()
        
        verse_keys = [(r[0], r[1]) for r in rows]
        verse_map = batch_compose_verse_texts(conn, verse_keys)
        
        results = []
        for s, a in verse_keys:
            results.append({"ref": f"{s}:{a}", "text": verse_map.get((s, a), "")})
        return {"total": len(results), "results": results}
