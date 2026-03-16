"""Context tools: morphology-aware entry lookup per word/feature.

Clarified naming:
- word_types: Unique word forms (DNA).
- word_instances: Specific occurrences.
"""

import json
from mcp.server.fastmcp import FastMCP

from ..db import get_connection
from ..utils.units import compose_verse_text, compose_word_text, entries_at_verse
from ..utils.features import TERM_TYPE_TO_FEATURE

mcp: FastMCP


def _feature_to_fk_col(feature_type: str) -> str | None:
    mapping = {
        'root': 'root_id', 'lemma': 'lemma_id', 'pos': 'pos_id',
        'verb_form': 'verb_form_id', 'voice': 'voice_id', 'mood': 'mood_id',
        'aspect': 'aspect_id', 'person': 'person_id', 'number': 'number_id',
        'gender': 'gender_id', 'case_value': 'case_value_id',
    }
    return mapping.get(feature_type)


def register(server: FastMCP):
    global mcp
    mcp = server

    @mcp.tool()
    def get_verse_with_context(surah: int, ayah: int) -> dict:
        """Retrieve a verse with its full morphological context and related research."""
        conn = get_connection()
        verse_text = compose_verse_text(conn, surah, ayah)
        if not verse_text: return {"error": "Verse not found"}

        # Get words with morphology
        rows = conn.execute(
            """SELECT wi.id as instance_id, wi.word_index, wi.word_type_id,
                      mt.id as morpheme_type_id, mt.uthmani_text as form,
                      rf_root.lookup_key as root, rf_lemma.lookup_key as lemma,
                      rf_pos.lookup_key as pos
               FROM word_instances wi
               JOIN word_type_morphemes wtm ON wi.word_type_id = wtm.word_type_id
               JOIN morpheme_types mt ON wtm.morpheme_type_id = mt.id
               LEFT JOIN features rf_root ON mt.root_id = rf_root.id
               LEFT JOIN features rf_lemma ON mt.lemma_id = rf_lemma.id
               LEFT JOIN features rf_pos ON mt.pos_id = rf_pos.id
               WHERE wi.verse_surah = ? AND wi.verse_ayah = ?
               ORDER BY wi.word_index, wtm.position""",
            (surah, ayah)
        ).fetchall()

        words = {}
        for r in rows:
            w = words.setdefault(r['word_index'], {"text": "", "morphemes": []})
            m = {"form": r['form']}
            if r['root']: m['root'] = r['root']
            if r['lemma']: m['lemma'] = r['lemma']
            if r['pos']: m['pos'] = r['pos']
            w["morphemes"].append(m)

        seen_types = {}
        for r in rows:
            if r['word_index'] not in seen_types:
                seen_types[r['word_index']] = r['word_type_id']
        for idx in words:
            words[idx]["text"] = compose_word_text(conn, seen_types.get(idx, 0))

        # Fetch direct entries (compact)
        direct = conn.execute(
            "SELECT address, content, phase, anchor_type, anchor_ids FROM holonomic_entries WHERE anchor_type='word_instance' AND anchor_ids LIKE ?",
            (f"{surah}:{ayah}%",)
        ).fetchall()

        return {
            "ref": f"{surah}:{ayah}", "text": verse_text,
            "words": words, "entries": [dict(e) for e in direct]
        }

    @mcp.tool()
    def get_feature_context(feature_type: str, value: str) -> dict:
        """Get context for a linguistic feature, including related entries and occurrences."""
        conn = get_connection()
        fk_col = _feature_to_fk_col(feature_type)
        if not fk_col: return {"error": "Unsupported feature type"}

        # Resolve feature ID
        mapping = TERM_TYPE_TO_FEATURE.get(feature_type)
        if not mapping: return {"error": "Feature mapping not found"}
        ft, _ = mapping
        feat_row = conn.execute("SELECT id FROM features WHERE feature_type=? AND lookup_key=?", (ft, value)).fetchone()
        if not feat_row: return {"error": "Feature not found"}
        fid = feat_row[0]

        # 1. Direct entries (anchored to this feature)
        direct = conn.execute(
            "SELECT address, content, phase, category FROM holonomic_entries WHERE anchor_type=? AND anchor_ids LIKE ?",
            (feature_type, f"%{fid}%")
        ).fetchall()

        # 2. Compositional entries (bubbles up from words using this feature)
        comp = conn.execute(
            f"""SELECT DISTINCT e.address, e.content, e.phase, e.category FROM holonomic_entries e
               JOIN word_type_morphemes wtm ON e.anchor_ids = CAST(wtm.word_type_id AS TEXT)
               JOIN morpheme_types mt ON wtm.morpheme_type_id = mt.id
               WHERE e.anchor_type='word_type' AND mt.{fk_col} = ?""",
            (fid,)
        ).fetchall()

        return {
            "feature": {"type": feature_type, "value": value, "id": fid},
            "direct_entries": [dict(e) for e in direct],
            "compositional_entries": [dict(e) for e in comp]
        }
