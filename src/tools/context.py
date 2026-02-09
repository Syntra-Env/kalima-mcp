"""Verse context tool: morphology-aware entry lookup per word."""

import json

from mcp.server.fastmcp import FastMCP

from ..db import get_connection

mcp: FastMCP


def register(server: FastMCP):
    global mcp
    mcp = server

    @mcp.tool()
    def get_verse_with_context(
        surah: int,
        ayah: int,
        include_root_entries: bool = True,
        include_form_entries: bool = True,
        include_pos_entries: bool = True,
    ) -> dict:
        """Get a verse with morphology-aware entry context.

        For each word, surfaces related entries based on its root, verb form,
        and POS from scope-based matching.
        """
        conn = get_connection()

        # Build in-memory ref lookups from unified ref_features table
        pos_lookup = {}
        morph_lookup: dict[str, dict[str, dict]] = {}
        dep_lookup = {}

        for r in conn.execute(
            "SELECT feature_type, category, lookup_key, label_ar, label_en FROM ref_features "
            "WHERE feature_type IN ('pos', 'morph', 'dep_rel')"
        ).fetchall():
            ft = r["feature_type"]
            if ft == "pos":
                pos_lookup[r["lookup_key"]] = {"pos_ar": r["label_ar"], "pos_en": r["label_en"]}
            elif ft == "morph":
                morph_lookup.setdefault(r["category"], {})[r["lookup_key"]] = {
                    "ar": r["label_ar"], "en": r["label_en"]
                }
            elif ft == "dep_rel":
                dep_lookup[r["lookup_key"]] = r["label_ar"]

        # Get the verse text
        verse_row = conn.execute(
            "SELECT surah_number, ayah_number, text FROM verse_texts WHERE surah_number = ? AND ayah_number = ?",
            (surah, ayah)
        ).fetchone()

        if not verse_row:
            return {"error": f"Verse {surah}:{ayah} not found"}

        verse = dict(verse_row)

        # Get all tokens and their segments for this verse, resolving FK columns to text
        tokens = conn.execute(
            """SELECT
                t.id as token_id,
                t.text as token_text,
                t.token_index,
                rf_root.lookup_key AS root,
                rf_lemma.lookup_key AS lemma,
                rf_pos.lookup_key AS pos,
                rf_vf.lookup_key AS verb_form,
                rf_asp.lookup_key AS aspect,
                rf_mood.lookup_key AS mood,
                rf_case.lookup_key AS case_value,
                rf_dep.lookup_key AS dependency_rel,
                rf_dn.lookup_key AS derived_noun_type
            FROM tokens t
            LEFT JOIN segments s ON s.token_id = t.id
            LEFT JOIN ref_features rf_root ON s.root_id = rf_root.id
            LEFT JOIN ref_features rf_lemma ON s.lemma_id = rf_lemma.id
            LEFT JOIN ref_features rf_pos ON s.pos_id = rf_pos.id
            LEFT JOIN ref_features rf_vf ON s.verb_form_id = rf_vf.id
            LEFT JOIN ref_features rf_asp ON s.aspect_id = rf_asp.id
            LEFT JOIN ref_features rf_mood ON s.mood_id = rf_mood.id
            LEFT JOIN ref_features rf_case ON s.case_value_id = rf_case.id
            LEFT JOIN ref_features rf_dep ON s.dependency_rel_id = rf_dep.id
            LEFT JOIN ref_features rf_dn ON s.derived_noun_type_id = rf_dn.id
            WHERE t.verse_surah = ? AND t.verse_ayah = ?
            ORDER BY t.token_index ASC""",
            (surah, ayah)
        ).fetchall()

        # For each token, find related entries based on scope matching
        words_with_context = []

        # Pre-load all pattern-scoped entries for efficient matching
        pattern_entries = []
        if include_form_entries or include_pos_entries:
            pattern_rows = conn.execute(
                "SELECT id, content, phase, scope_value FROM entries WHERE scope_type = 'pattern' AND scope_value IS NOT NULL"
            ).fetchall()
            for row in pattern_rows:
                try:
                    features = json.loads(row['scope_value'])
                    pattern_entries.append({
                        'entry_id': row['id'],
                        'entry_content': row['content'],
                        'entry_phase': row['phase'],
                        'features': features,
                    })
                except (json.JSONDecodeError, TypeError):
                    pass

        for token in tokens:
            related_entries = []

            # 1. Root-scoped entries: exact match on scope_value
            if include_root_entries and token['root']:
                root_entries = conn.execute(
                    """SELECT id as entry_id, content as entry_content, phase as entry_phase
                       FROM entries WHERE scope_type = 'root' AND scope_value = ?""",
                    (token['root'],)
                ).fetchall()
                for e in root_entries:
                    related_entries.append({
                        **dict(e),
                        "matched_feature_type": "root",
                        "matched_feature_value": token['root'],
                    })

            # 2. Pattern-scoped entries: check if token matches ALL features in the pattern
            token_dict = dict(token)
            for pe in pattern_entries:
                features = pe['features']
                match = True
                matched_type = None
                matched_value = None

                for feat_key, feat_val in features.items():
                    token_val = token_dict.get(feat_key)
                    if token_val is None or token_val != feat_val:
                        match = False
                        break
                    if matched_type is None:
                        matched_type = feat_key
                        matched_value = feat_val

                if match and matched_type:
                    # Check filter flags
                    has_form = any(k in features for k in ('verb_form', 'aspect', 'mood'))
                    has_pos = 'pos' in features
                    if (has_form and not include_form_entries) or (has_pos and not include_pos_entries):
                        continue
                    related_entries.append({
                        "entry_id": pe['entry_id'],
                        "entry_content": pe['entry_content'],
                        "entry_phase": pe['entry_phase'],
                        "matched_feature_type": "pattern",
                        "matched_feature_value": json.dumps(features, ensure_ascii=False),
                    })

            # Build enriched token dict with human-readable labels
            word = {
                "token_text": token['token_text'],
                "token_index": token['token_index'],
                "root": token['root'],
                "lemma": token['lemma'],
                "pos": token['pos'],
                "verb_form": token['verb_form'],
                "aspect": token['aspect'],
                "related_entries": related_entries,
            }

            # Decorate with ref table labels
            if token['pos'] and token['pos'] in pos_lookup:
                word["pos_ar"] = pos_lookup[token['pos']]["pos_ar"]
                word["pos_en"] = pos_lookup[token['pos']]["pos_en"]
            if token['case_value']:
                case_info = morph_lookup.get("NominalCase", {}).get(token['case_value'])
                if case_info:
                    word["case_ar"] = case_info["ar"]
                    word["case_en"] = case_info["en"]
            if token['derived_noun_type']:
                dn_info = morph_lookup.get("DerivedNoun", {}).get(token['derived_noun_type'])
                if dn_info:
                    word["derived_noun_ar"] = dn_info["ar"]
                    word["derived_noun_en"] = dn_info["en"]
            if token['mood']:
                mood_info = morph_lookup.get("VerbMood", {}).get(token['mood'])
                if mood_info:
                    word["mood_ar"] = mood_info["ar"]
                    word["mood_en"] = mood_info["en"]
            if token['aspect']:
                asp_info = morph_lookup.get("VerbState", {}).get(token['aspect'])
                if asp_info:
                    word["aspect_ar"] = asp_info["ar"]
                    word["aspect_en"] = asp_info["en"]
            if token['dependency_rel'] and token['dependency_rel'] in dep_lookup:
                word["dependency_rel_ar"] = dep_lookup[token['dependency_rel']]

            words_with_context.append(word)

        # Get verse-scoped entries for this verse + their parent entries
        scope_value = f"{surah}:{ayah}"
        direct_entries = conn.execute(
            """SELECT
                e.id as entry_id,
                e.content as entry_content,
                e.phase as entry_phase,
                ed.dependency_type as verification
            FROM entries e
            LEFT JOIN entry_dependencies ed ON ed.entry_id = e.id
            WHERE e.scope_type = 'verse' AND e.scope_value = ?
            ORDER BY e.created_at DESC""",
            (scope_value,)
        ).fetchall()

        return {
            "verse": verse,
            "words_with_context": words_with_context,
            "direct_verse_entries": [dict(e) for e in direct_entries],
        }
