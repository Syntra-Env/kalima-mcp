"""Context tools: morphology-aware entry lookup per word/feature."""

import json

from mcp.server.fastmcp import FastMCP

from ..db import get_connection
from ..utils.units import entries_at_verse
from ..utils.features import TERM_TYPE_TO_FEATURE

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

        # Build in-memory ref lookups from unified features table
        pos_lookup = {}
        morph_lookup: dict[str, dict[str, dict]] = {}
        dep_lookup = {}

        for r in conn.execute(
            "SELECT feature_type, category, lookup_key, label_ar, label_en FROM features "
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

        # Get all words and their morphemes for this verse, resolving FK columns to text
        words_rows = conn.execute(
            """SELECT
                w.id as word_id,
                w.text as word_text,
                w.word_index,
                rf_root.lookup_key AS root,
                rf_lemma.lookup_key AS lemma,
                rf_pos.lookup_key AS pos,
                rf_vf.lookup_key AS verb_form,
                rf_asp.lookup_key AS aspect,
                rf_mood.lookup_key AS mood,
                rf_case.lookup_key AS case_value,
                rf_dep.lookup_key AS dependency_rel,
                rf_dn.lookup_key AS derived_noun_type
            FROM words w
            LEFT JOIN morphemes m ON m.word_id = w.id
            LEFT JOIN features rf_root ON m.root_id = rf_root.id
            LEFT JOIN features rf_lemma ON m.lemma_id = rf_lemma.id
            LEFT JOIN features rf_pos ON m.pos_id = rf_pos.id
            LEFT JOIN features rf_vf ON m.verb_form_id = rf_vf.id
            LEFT JOIN features rf_asp ON m.aspect_id = rf_asp.id
            LEFT JOIN features rf_mood ON m.mood_id = rf_mood.id
            LEFT JOIN features rf_case ON m.case_value_id = rf_case.id
            LEFT JOIN features rf_dep ON m.dependency_rel_id = rf_dep.id
            LEFT JOIN features rf_dn ON m.derived_noun_type_id = rf_dn.id
            WHERE w.verse_surah = ? AND w.verse_ayah = ?
            ORDER BY w.word_index ASC""",
            (surah, ayah)
        ).fetchall()

        if not words_rows:
            return {"error": f"Verse {surah}:{ayah} not found"}

        # Group rows by word_index (one word may have multiple morphemes)
        from collections import OrderedDict
        word_groups: OrderedDict[int, list] = OrderedDict()
        for row in words_rows:
            word_groups.setdefault(row['word_index'], []).append(row)

        # Compose verse text using one text per unique word
        verse = {
            "surah_number": surah,
            "ayah_number": ayah,
            "text": ' '.join(rows[0]['word_text'] for rows in word_groups.values()),
        }

        # For each word, find related entries based on feature matching
        words_with_context = []

        # Pre-load pattern entries (cross-cutting entries with linguistic features in content)
        pattern_entries = []
        if include_form_entries or include_pos_entries:
            pattern_rows = conn.execute(
                """SELECT id, content, phase FROM entries
                   WHERE content LIKE '%Linguistic features:%'
                     AND feature_id IS NULL
                     AND NOT EXISTS (SELECT 1 FROM entry_locations el WHERE el.entry_id = entries.id)"""
            ).fetchall()
            for row in pattern_rows:
                content = row['content']
                idx = content.find('Linguistic features: ')
                if idx >= 0:
                    json_str = content[idx + len('Linguistic features: '):]
                    try:
                        features = json.loads(json_str)
                        pattern_entries.append({
                            'entry_id': row['id'],
                            'entry_content': row['content'],
                            'entry_phase': row['phase'],
                            'features': features,
                        })
                    except (json.JSONDecodeError, TypeError):
                        pass

        # Build root lookup: root lookup_key -> features.id for resolving feature_id
        root_feature_ids = {}
        for r in conn.execute(
            "SELECT id, lookup_key FROM features WHERE feature_type = 'root' AND category IS NULL"
        ).fetchall():
            root_feature_ids[r['lookup_key']] = r['id']

        for word_row in words_rows:
            related_entries = []

            # 1. Feature-anchored entries for this word's root
            if include_root_entries and word_row['root']:
                rf_id = root_feature_ids.get(word_row['root'])
                if rf_id:
                    root_entries = conn.execute(
                        """SELECT id as entry_id, content as entry_content, phase as entry_phase
                           FROM entries WHERE feature_id = ?""",
                        (rf_id,)
                    ).fetchall()
                    for e in root_entries:
                        related_entries.append({
                            **dict(e),
                            "matched_feature_type": "root",
                            "matched_feature_value": word_row['root'],
                        })

            # 2. Pattern-scoped entries: check if word matches ALL features in the pattern
            word_dict = dict(word_row)
            for pe in pattern_entries:
                features = pe['features']
                match = True
                matched_type = None
                matched_value = None

                for feat_key, feat_val in features.items():
                    word_val = word_dict.get(feat_key)
                    if word_val is None or word_val != feat_val:
                        match = False
                        break
                    if matched_type is None:
                        matched_type = feat_key
                        matched_value = feat_val

                if match and matched_type:
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

            # Build enriched word dict with human-readable labels
            word = {
                "word_text": word_row['word_text'],
                "word_index": word_row['word_index'],
                "root": word_row['root'],
                "lemma": word_row['lemma'],
                "pos": word_row['pos'],
                "verb_form": word_row['verb_form'],
                "aspect": word_row['aspect'],
                "related_entries": related_entries,
            }

            # Decorate with ref table labels
            if word_row['pos'] and word_row['pos'] in pos_lookup:
                word["pos_ar"] = pos_lookup[word_row['pos']]["pos_ar"]
                word["pos_en"] = pos_lookup[word_row['pos']]["pos_en"]
            if word_row['case_value']:
                case_info = morph_lookup.get("NominalCase", {}).get(word_row['case_value'])
                if case_info:
                    word["case_ar"] = case_info["ar"]
                    word["case_en"] = case_info["en"]
            if word_row['derived_noun_type']:
                dn_info = morph_lookup.get("DerivedNoun", {}).get(word_row['derived_noun_type'])
                if dn_info:
                    word["derived_noun_ar"] = dn_info["ar"]
                    word["derived_noun_en"] = dn_info["en"]
            if word_row['mood']:
                mood_info = morph_lookup.get("VerbMood", {}).get(word_row['mood'])
                if mood_info:
                    word["mood_ar"] = mood_info["ar"]
                    word["mood_en"] = mood_info["en"]
            if word_row['aspect']:
                asp_info = morph_lookup.get("VerbState", {}).get(word_row['aspect'])
                if asp_info:
                    word["aspect_ar"] = asp_info["ar"]
                    word["aspect_en"] = asp_info["en"]
            if word_row['dependency_rel'] and word_row['dependency_rel'] in dep_lookup:
                word["dependency_rel_ar"] = dep_lookup[word_row['dependency_rel']]

            words_with_context.append(word)

        # Get verse entries for this verse + their parent entries
        verse_entry_ids = entries_at_verse(conn, surah, ayah)
        direct_entries = []
        if verse_entry_ids:
            placeholders = ",".join("?" for _ in verse_entry_ids)
            direct_entries = conn.execute(
                f"""SELECT
                    e.id as entry_id,
                    e.content as entry_content,
                    e.phase as entry_phase,
                    el.verification
                FROM entries e
                JOIN entry_locations el ON el.entry_id = e.id
                WHERE e.id IN ({placeholders})
                  AND el.surah = ? AND el.ayah_start = ?
                ORDER BY e.created_at DESC""",
                verse_entry_ids + [surah, ayah]
            ).fetchall()

        return {
            "verse": verse,
            "words_with_context": words_with_context,
            "direct_verse_entries": [dict(e) for e in direct_entries],
        }

    @mcp.tool()
    def get_feature_context(
        feature_type: str,
        value: str,
        include_related_features: bool = True,
        include_verses: bool = True,
        include_cross_cutting: bool = True,
        verse_limit: int = 20,
    ) -> dict:
        """Get everything known about a feature: its hierarchy, entries, and verses.

        Traverses the feature hierarchy to surface all related entries.
        e.g. for root رحم: finds the root entry, all lemma entries,
        all verse-evidence entries, and cross-cutting entries linked to any of them.

        feature_type: root, lemma, pos, verb_form, aspect, mood, voice,
                      person, number, gender, case_value, state,
                      derived_noun_type, dependency_rel, role
        value: the lookup_key (e.g. 'رحم' for root, 'V' for pos)
        """
        conn = get_connection()

        # Resolve feature_type to (db_feature_type, category) using the mapping
        mapping = TERM_TYPE_TO_FEATURE.get(feature_type)
        if not mapping:
            return {"error": f"Unknown feature_type '{feature_type}'. Valid: {', '.join(TERM_TYPE_TO_FEATURE.keys())}"}

        db_ft, db_cat = mapping

        # Find the feature row
        if db_cat:
            feat_row = conn.execute(
                "SELECT id, feature_type, category, lookup_key, label_ar, label_en, frequency FROM features WHERE feature_type = ? AND category = ? AND lookup_key = ?",
                (db_ft, db_cat, value)
            ).fetchone()
        else:
            feat_row = conn.execute(
                "SELECT id, feature_type, category, lookup_key, label_ar, label_en, frequency FROM features WHERE feature_type = ? AND category IS NULL AND lookup_key = ?",
                (db_ft, value)
            ).fetchone()

        if not feat_row:
            return {"error": f"Feature not found: {feature_type}={value}"}

        feature = dict(feat_row)
        feature_id = feature['id']

        # Collect all feature IDs in the hierarchy
        all_feature_ids = {feature_id}
        related_features = []

        if include_related_features:
            if feature_type == 'root':
                # Root -> find all lemmas derived from this root
                lemma_rows = conn.execute(
                    """SELECT DISTINCT f.id, f.lookup_key, f.label_ar, f.label_en, f.frequency
                       FROM features f
                       JOIN morphemes m ON m.lemma_id = f.id
                       WHERE m.root_id = ?""",
                    (feature_id,)
                ).fetchall()
                for lr in lemma_rows:
                    all_feature_ids.add(lr['id'])
                    related_features.append({
                        "feature_id": lr['id'],
                        "type": "lemma",
                        "value": lr['lookup_key'],
                        "label_ar": lr['label_ar'],
                        "frequency": lr['frequency'],
                        "relation": "derived_from_root",
                    })

            elif feature_type == 'lemma':
                # Lemma -> find its root
                root_row = conn.execute(
                    """SELECT DISTINCT f.id, f.lookup_key, f.label_ar
                       FROM features f
                       JOIN morphemes m ON m.root_id = f.id
                       WHERE m.lemma_id = ?""",
                    (feature_id,)
                ).fetchone()
                if root_row:
                    all_feature_ids.add(root_row['id'])
                    related_features.append({
                        "feature_id": root_row['id'],
                        "type": "root",
                        "value": root_row['lookup_key'],
                        "label_ar": root_row['label_ar'],
                        "relation": "parent_root",
                    })
                    # Also find sibling lemmas from the same root
                    sibling_rows = conn.execute(
                        """SELECT DISTINCT f.id, f.lookup_key, f.label_ar, f.frequency
                           FROM features f
                           JOIN morphemes m ON m.lemma_id = f.id
                           WHERE m.root_id = ? AND f.id != ?""",
                        (root_row['id'], feature_id)
                    ).fetchall()
                    for sr in sibling_rows:
                        all_feature_ids.add(sr['id'])
                        related_features.append({
                            "feature_id": sr['id'],
                            "type": "lemma",
                            "value": sr['lookup_key'],
                            "label_ar": sr['label_ar'],
                            "frequency": sr['frequency'],
                            "relation": "sibling_lemma",
                        })

        # Collect entries anchored to any feature in the tree
        entries = []
        if all_feature_ids:
            placeholders = ",".join("?" for _ in all_feature_ids)
            entry_rows = conn.execute(
                f"""SELECT e.id, e.content, e.phase, e.category, e.feature_id,
                           f.feature_type as anchored_type, f.lookup_key as anchored_value
                    FROM entries e
                    JOIN features f ON e.feature_id = f.id
                    WHERE e.feature_id IN ({placeholders})
                    ORDER BY e.updated_at DESC""",
                list(all_feature_ids)
            ).fetchall()
            for er in entry_rows:
                entries.append({**dict(er), "source": "feature_anchored"})

        # Collect verse-evidence locations from the above entries
        entry_ids = [e['id'] for e in entries]
        if entry_ids:
            ep = ",".join("?" for _ in entry_ids)
            evidence_rows = conn.execute(
                f"""SELECT el.entry_id, el.surah, el.ayah_start as ayah,
                           el.verification, el.notes
                    FROM entry_locations el
                    WHERE el.entry_id IN ({ep})
                      AND el.verification IS NOT NULL
                    ORDER BY el.surah, el.ayah_start""",
                entry_ids
            ).fetchall()
            for ev in evidence_rows:
                entries.append({**dict(ev), "source": "verse_evidence"})

        # Find verses where this feature appears (through morphemes)
        verses = []
        if include_verses:
            fk_col = _feature_to_fk_col(feature_type)
            if fk_col:
                verse_rows = conn.execute(
                    f"""SELECT DISTINCT w.verse_surah as surah, w.verse_ayah as ayah
                        FROM morphemes m
                        JOIN words w ON m.word_id = w.id
                        WHERE m.{fk_col} = ?
                        ORDER BY w.verse_surah, w.verse_ayah
                        LIMIT ?""",
                    (feature_id, verse_limit)
                ).fetchall()
                for vr in verse_rows:
                    v = {"surah": vr['surah'], "ayah": vr['ayah']}
                    # Check for location-anchored entries at this verse
                    verse_eids = entries_at_verse(conn, vr['surah'], vr['ayah'])
                    if verse_eids:
                        placeholders_v = ",".join("?" for _ in verse_eids)
                        ve = conn.execute(
                            f"SELECT id, content, phase FROM entries WHERE id IN ({placeholders_v})",
                            verse_eids
                        ).fetchall()
                        if ve:
                            v["entries"] = [dict(e) for e in ve]
                    verses.append(v)

        # Find cross-cutting entries discovered through shared verse locations
        cross_cutting = []
        if include_cross_cutting and entry_ids:
            # Find entries that share verses with our feature-anchored entries
            ep = ",".join("?" for _ in entry_ids)
            shared_loc_rows = conn.execute(
                f"""SELECT DISTINCT e2.id, e2.content, e2.phase, e2.category
                    FROM entry_locations el1
                    JOIN entry_locations el2 ON el1.surah = el2.surah
                        AND el1.ayah_start = el2.ayah_start
                        AND el1.entry_id != el2.entry_id
                    JOIN entries e2 ON e2.id = el2.entry_id
                    WHERE el1.entry_id IN ({ep})
                      AND e2.id NOT IN ({ep})
                    ORDER BY e2.updated_at DESC
                    LIMIT 20""",
                entry_ids + entry_ids
            ).fetchall()
            for cc in shared_loc_rows:
                cross_cutting.append(dict(cc))

        return {
            "feature": feature,
            "related_features": related_features,
            "entries": entries,
            "verses": verses,
            "cross_cutting": cross_cutting,
            "summary": {
                "feature_ids_in_tree": len(all_feature_ids),
                "anchored_entries": sum(1 for e in entries if e.get('source') == 'feature_anchored'),
                "verse_evidence_entries": sum(1 for e in entries if e.get('source') == 'verse_evidence'),
                "verses_found": len(verses),
                "cross_cutting_entries": len(cross_cutting),
            },
        }


def _feature_to_fk_col(feature_type: str) -> str | None:
    """Map a logical feature name to the FK column in morphemes."""
    mapping = {
        'root': 'root_id', 'lemma': 'lemma_id', 'pos': 'pos_id',
        'verb_form': 'verb_form_id', 'aspect': 'aspect_id', 'mood': 'mood_id',
        'voice': 'voice_id', 'person': 'person_id', 'number': 'number_id',
        'gender': 'gender_id', 'case_value': 'case_value_id',
        'state': 'state_id', 'derived_noun_type': 'derived_noun_type_id',
        'dependency_rel': 'dependency_rel_id', 'role': 'role_id',
    }
    return mapping.get(feature_type)
