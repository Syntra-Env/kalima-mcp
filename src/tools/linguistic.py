"""Linguistic analysis tools: morphological search, evidence, term linking."""

import json
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from ..db import get_connection, save_database
from ..utils.features import TERM_TYPE_TO_FEATURE
from ..utils.short_id import generate_entry_id
from ..utils.units import verse_exists, batch_compose_verse_texts
from .research import _find_duplicate
from .workflow import _compute_confidence

mcp: FastMCP

# Map user-friendly names to database codes
_FEATURE_MAPPINGS: dict[str, dict[str, str]] = {
    "pos": {
        "verb": "V",
        "noun": "N",
        "adjective": "ADJ",
        "pronoun": "PRON",
        "preposition": "P",
        "particle": "T",
    },
    "aspect": {
        "imperfective": "IMPF",
        "present": "IMPF",
        "perfective": "PERF",
        "past": "PERF",
        "imperative": "IMPV",
    },
    "mood": {
        "jussive": "MOOD:JUS",
        "subjunctive": "MOOD:SUBJ",
    },
}


def _normalize_feature(key: str, value: str) -> str:
    # Strip dashes from root values (DB stores قول not ق-و-ل)
    if key == 'root':
        value = value.replace('-', '')
    lower = value.lower()
    return _FEATURE_MAPPINGS.get(key, {}).get(lower, value)


def _resolve_feature_id(conn, feature_name: str, value: str) -> int | None:
    """Resolve a feature name + value to a features.id."""
    ft, cat = TERM_TYPE_TO_FEATURE[feature_name]
    if cat:
        row = conn.execute(
            "SELECT id FROM features WHERE feature_type = ? AND category = ? AND lookup_key = ?",
            (ft, cat, value)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id FROM features WHERE feature_type = ? AND category IS NULL AND lookup_key = ?",
            (ft, value)
        ).fetchone()
    return row['id'] if row else None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def register(server: FastMCP):
    global mcp
    mcp = server

    @mcp.tool()
    def search_by_linguistic_features(
        pos: str | None = None,
        aspect: str | None = None,
        mood: str | None = None,
        verb_form: str | None = None,
        voice: str | None = None,
        person: str | None = None,
        number: str | None = None,
        gender: str | None = None,
        root: str | None = None,
        lemma: str | None = None,
        case_value: str | None = None,
        dependency_rel: str | None = None,
        role: str | None = None,
        surah: int | None = None,
        limit: int = 50,
    ) -> dict:
        """Search verses by linguistic features like part of speech, verb form, mood, aspect, root, etc."""
        conn = get_connection()

        # Build WHERE clause dynamically using FK joins
        features = {
            "pos": pos, "aspect": aspect, "mood": mood, "verb_form": verb_form,
            "voice": voice, "person": person, "number": number, "gender": gender,
            "root": root, "lemma": lemma, "case_value": case_value,
            "dependency_rel": dependency_rel, "role": role,
        }

        conditions = []
        params: list = []

        for key, val in features.items():
            if val is not None:
                normalized = _normalize_feature(key, str(val))
                fk_id = _resolve_feature_id(conn, key, normalized)
                if fk_id is None:
                    return {"error": f"Feature value not found: {key}={normalized}"}
                conditions.append(f"m.{key}_id = ?")
                params.append(fk_id)

        if surah is not None:
            conditions.append("w.verse_surah = ?")
            params.append(surah)

        if not conditions:
            return {"error": "At least one linguistic feature must be specified"}

        where_clause = " AND ".join(conditions)
        params.append(limit)

        # Build query_info from features
        query_info: dict = {}
        if root is not None:
            normalized_root = _normalize_feature("root", root)
            ref_row = conn.execute(
                "SELECT lookup_key, frequency FROM features WHERE feature_type = 'root' AND lookup_key = ?",
                (normalized_root,)
            ).fetchone()
            query_info["root"] = normalized_root
            if ref_row:
                query_info["root_ar"] = ref_row["lookup_key"]
                query_info["frequency"] = ref_row["frequency"]
        if lemma is not None:
            normalized_lemma = _normalize_feature("lemma", lemma)
            ref_row = conn.execute(
                "SELECT lookup_key, frequency FROM features WHERE feature_type = 'lemma' AND lookup_key = ?",
                (normalized_lemma,)
            ).fetchone()
            query_info["lemma"] = normalized_lemma
            if ref_row:
                query_info["lemma_ar"] = ref_row["lookup_key"]
                query_info["frequency"] = ref_row["frequency"]

        # Get matching verses
        verse_rows = conn.execute(
            f"""SELECT DISTINCT
                w.verse_surah AS surah_number,
                w.verse_ayah AS ayah_number
            FROM morphemes m
            JOIN words w ON m.word_id = w.id
            WHERE {where_clause}
            ORDER BY w.verse_surah ASC, w.verse_ayah ASC
            LIMIT ?""",
            params
        ).fetchall()

        # Total count (before limit)
        count_params = params[:-1]  # exclude the limit param
        total = conn.execute(
            f"""SELECT COUNT(DISTINCT w.verse_surah || ':' || w.verse_ayah)
            FROM morphemes m
            JOIN words w ON m.word_id = w.id
            WHERE {where_clause}""",
            count_params
        ).fetchone()[0]

        query_info["total_verses"] = total
        query_info["verses_returned"] = len(verse_rows)

        # Batch-compose verse texts
        verse_keys = [(r['surah_number'], r['ayah_number']) for r in verse_rows]
        verse_text_map = batch_compose_verse_texts(conn, verse_keys)

        # For each verse, fetch only the matching morphemes (not every morpheme in the verse)
        results = []
        for verse in verse_rows:
            v = dict(verse)
            v['text'] = verse_text_map.get((v['surah_number'], v['ayah_number']), '')

            matching_morphemes = conn.execute(
                f"""SELECT m.id, m.word_id, m.form,
                    rf_root.lookup_key AS root,
                    rf_lemma.lookup_key AS lemma,
                    rf_pos.lookup_key AS pos,
                    rf_vf.lookup_key AS verb_form,
                    rf_voice.lookup_key AS voice,
                    rf_mood.lookup_key AS mood,
                    rf_asp.lookup_key AS aspect,
                    rf_per.lookup_key AS person,
                    rf_num.lookup_key AS number,
                    rf_gen.lookup_key AS gender,
                    rf_case.lookup_key AS case_value,
                    rf_dep.lookup_key AS dependency_rel
                FROM morphemes m
                JOIN words w ON m.word_id = w.id
                LEFT JOIN features rf_root ON m.root_id = rf_root.id
                LEFT JOIN features rf_lemma ON m.lemma_id = rf_lemma.id
                LEFT JOIN features rf_pos ON m.pos_id = rf_pos.id
                LEFT JOIN features rf_vf ON m.verb_form_id = rf_vf.id
                LEFT JOIN features rf_voice ON m.voice_id = rf_voice.id
                LEFT JOIN features rf_mood ON m.mood_id = rf_mood.id
                LEFT JOIN features rf_asp ON m.aspect_id = rf_asp.id
                LEFT JOIN features rf_per ON m.person_id = rf_per.id
                LEFT JOIN features rf_num ON m.number_id = rf_num.id
                LEFT JOIN features rf_gen ON m.gender_id = rf_gen.id
                LEFT JOIN features rf_case ON m.case_value_id = rf_case.id
                LEFT JOIN features rf_dep ON m.dependency_rel_id = rf_dep.id
                WHERE w.verse_surah = ? AND w.verse_ayah = ?
                  AND {where_clause}
                ORDER BY w.word_index ASC""",
                [v['surah_number'], v['ayah_number']] + count_params
            ).fetchall()

            v['matching_morphemes'] = [dict(m) for m in matching_morphemes]
            results.append(v)

        return {"query_info": query_info, "result": results}

    @mcp.tool()
    def compare_roots(root1: str, root2: str, limit: int = 30) -> dict:
        """Find verses where two roots co-occur. Core tool for cross-referencing Quranic terms."""
        conn = get_connection()

        r1 = _normalize_feature("root", root1)
        r2 = _normalize_feature("root", root2)

        # Resolve to FK IDs
        r1_id = _resolve_feature_id(conn, "root", r1)
        r2_id = _resolve_feature_id(conn, "root", r2)

        if r1_id is None:
            return {"error": f"Root not found: {r1}"}
        if r2_id is None:
            return {"error": f"Root not found: {r2}"}

        # Ref info for each root
        def _root_info(r: str) -> dict:
            info: dict = {"root": r}
            row = conn.execute(
                "SELECT lookup_key, frequency FROM features WHERE feature_type = 'root' AND lookup_key = ?", (r,)
            ).fetchone()
            if row:
                info["root_ar"] = row["lookup_key"]
                info["frequency"] = row["frequency"]
            return info

        # Find co-occurring verses using FK IDs
        co_rows = conn.execute(
            """SELECT DISTINCT w1.verse_surah AS surah, w1.verse_ayah AS ayah
            FROM morphemes m1
            JOIN words w1 ON m1.word_id = w1.id
            JOIN morphemes m2 ON m2.root_id = ?
            JOIN words w2 ON m2.word_id = w2.id
                AND w1.verse_surah = w2.verse_surah
                AND w1.verse_ayah = w2.verse_ayah
            WHERE m1.root_id = ?
            ORDER BY w1.verse_surah ASC, w1.verse_ayah ASC
            LIMIT ?""",
            (r2_id, r1_id, limit)
        ).fetchall()

        # Batch-compose verse texts
        co_keys = [(r['surah'], r['ayah']) for r in co_rows]
        co_text_map = batch_compose_verse_texts(conn, co_keys)

        co_occurrences = []
        for row in co_rows:
            s, a = row["surah"], row["ayah"]
            # Get the specific words for each root in this verse
            w1 = conn.execute(
                """SELECT DISTINCT w.text FROM morphemes m
                   JOIN words w ON m.word_id = w.id
                   WHERE m.root_id = ? AND w.verse_surah = ? AND w.verse_ayah = ?""",
                (r1_id, s, a)
            ).fetchall()
            w2 = conn.execute(
                """SELECT DISTINCT w.text FROM morphemes m
                   JOIN words w ON m.word_id = w.id
                   WHERE m.root_id = ? AND w.verse_surah = ? AND w.verse_ayah = ?""",
                (r2_id, s, a)
            ).fetchall()
            co_occurrences.append({
                "surah": s, "ayah": a, "text": co_text_map.get((s, a), ''),
                "root1_words": [r["text"] for r in w1],
                "root2_words": [r["text"] for r in w2],
            })

        # Total count (may exceed limit)
        total = conn.execute(
            """SELECT COUNT(DISTINCT w1.verse_surah || ':' || w1.verse_ayah)
            FROM morphemes m1
            JOIN words w1 ON m1.word_id = w1.id
            JOIN morphemes m2 ON m2.root_id = ?
            JOIN words w2 ON m2.word_id = w2.id
                AND w1.verse_surah = w2.verse_surah
                AND w1.verse_ayah = w2.verse_ayah
            WHERE m1.root_id = ?""",
            (r2_id, r1_id)
        ).fetchone()[0]

        return {
            "root1": _root_info(r1),
            "root2": _root_info(r2),
            "co_occurrences": co_occurrences,
            "total_co_occurrences": total,
            "returned": len(co_occurrences),
        }

    @mcp.tool()
    def create_pattern_interpretation(
        description: str,
        pattern_type: str,
        interpretation: str,
        linguistic_features: dict | None = None,
        scope: str = "all_verses",
        phase: str = "hypothesis",
    ) -> dict:
        """Create a linguistic pattern with interpretation.

        Example: "Present tense verbs in the Quran indicate ongoing or future actions"
        Creates an entry with scope_type='pattern' and scope_value as JSON features.
        """
        conn = get_connection()
        try:
            now = _now()

            entry_content = f"{description}\n\nInterpretation: {interpretation}"
            if linguistic_features:
                entry_content += f"\n\nLinguistic features: {json.dumps(linguistic_features)}"

            existing_id = _find_duplicate(conn, entry_content)
            if existing_id:
                eid = existing_id
            else:
                eid = generate_entry_id(conn)
                # Cross-cutting entry (no feature_id) — patterns span multiple features
                conn.execute(
                    """INSERT INTO entries (id, content, phase, category, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (eid, entry_content, phase, "quranic_research", now, now)
                )

            save_database()

            return {
                "success": True,
                "entry_id": eid,
                "message": f"Pattern entry created: {eid}",
            }
        except Exception as e:
            return {"success": False, "entry_id": "", "message": f"Failed to create pattern interpretation: {e}"}

    @mcp.tool()
    def create_surah_theme(
        surah: int,
        theme: str,
        description: str | None = None,
        phase: str = "hypothesis",
    ) -> dict:
        """Create a thematic interpretation for an entire surah."""
        conn = get_connection()
        try:
            from ..utils.surahs import get_surah_name
            surah_name = get_surah_name(surah) or f"Surah {surah}"

            now = _now()

            entry_content = f"Surah {surah} ({surah_name}) - Theme: {theme}"
            if description:
                entry_content += f"\n\nDescription: {description}"

            existing_id = _find_duplicate(conn, entry_content)
            if existing_id:
                eid = existing_id
            else:
                eid = generate_entry_id(conn)
                # Cross-cutting entry (no feature_id) — surah themes span the whole surah
                conn.execute(
                    """INSERT INTO entries (id, content, phase, category, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (eid, entry_content, phase, "quranic_research", now, now)
                )

            save_database()

            return {
                "success": True,
                "entry_id": eid,
                "message": f"Surah theme created successfully for {surah_name}\nEntry ID: {eid}\nPhase: {phase}",
            }
        except Exception as e:
            return {"success": False, "entry_id": "", "message": f"Failed to create surah theme: {e}"}

    @mcp.tool()
    def update_morpheme(
        morpheme_id: str,
        verb_form: str | None = None,
        voice: str | None = None,
        mood: str | None = None,
        aspect: str | None = None,
        person: str | None = None,
        number: str | None = None,
        gender: str | None = None,
        case_value: str | None = None,
        dependency_rel: str | None = None,
        role: str | None = None,
    ) -> dict:
        """Update linguistic features on a morpheme by its id (e.g. "mor-2-282-78-0").

        Only provided (non-None) features are updated; others are left unchanged.
        Values are resolved against features. Pass the human-readable value
        (e.g. verb_form="(VI)", mood="MOOD:JUS", voice="PASS").
        """
        conn = get_connection()

        mor = conn.execute(
            "SELECT id FROM morphemes WHERE id = ?", (morpheme_id,)
        ).fetchone()
        if not mor:
            return {"error": f"Morpheme not found: {morpheme_id}"}

        features = {
            "verb_form": verb_form, "voice": voice, "mood": mood,
            "aspect": aspect, "person": person, "number": number,
            "gender": gender, "case_value": case_value,
            "dependency_rel": dependency_rel, "role": role,
        }

        updates = {}
        for key, val in features.items():
            if val is not None:
                normalized = _normalize_feature(key, val)
                fk_id = _resolve_feature_id(conn, key, normalized)
                if fk_id is None:
                    return {"error": f"Feature value not found: {key}={normalized}"}
                updates[f"{key}_id"] = fk_id

        if not updates:
            return {"error": "No features provided to update"}

        set_clause = ", ".join(f"{col} = ?" for col in updates)
        params = list(updates.values()) + [morpheme_id]
        conn.execute(f"UPDATE morphemes SET {set_clause} WHERE id = ?", params)
        save_database()

        # Return the updated morpheme
        updated = conn.execute(
            """SELECT m.id, m.word_id, m.form,
                rf_root.lookup_key AS root,
                rf_lemma.lookup_key AS lemma,
                rf_pos.lookup_key AS pos,
                rf_vf.lookup_key AS verb_form,
                rf_voice.lookup_key AS voice,
                rf_mood.lookup_key AS mood,
                rf_asp.lookup_key AS aspect,
                rf_per.lookup_key AS person,
                rf_num.lookup_key AS number,
                rf_gen.lookup_key AS gender,
                rf_case.lookup_key AS case_value,
                rf_dep.lookup_key AS dependency_rel
            FROM morphemes m
            LEFT JOIN features rf_root ON m.root_id = rf_root.id
            LEFT JOIN features rf_lemma ON m.lemma_id = rf_lemma.id
            LEFT JOIN features rf_pos ON m.pos_id = rf_pos.id
            LEFT JOIN features rf_vf ON m.verb_form_id = rf_vf.id
            LEFT JOIN features rf_voice ON m.voice_id = rf_voice.id
            LEFT JOIN features rf_mood ON m.mood_id = rf_mood.id
            LEFT JOIN features rf_asp ON m.aspect_id = rf_asp.id
            LEFT JOIN features rf_per ON m.person_id = rf_per.id
            LEFT JOIN features rf_num ON m.number_id = rf_num.id
            LEFT JOIN features rf_gen ON m.gender_id = rf_gen.id
            LEFT JOIN features rf_case ON m.case_value_id = rf_case.id
            LEFT JOIN features rf_dep ON m.dependency_rel_id = rf_dep.id
            WHERE m.id = ?""",
            (morpheme_id,)
        ).fetchone()

        return {"success": True, "morpheme": dict(updated)}

    @mcp.tool()
    def add_verse_evidence(
        entry_id: str,
        surah: int,
        ayah: int,
        verification: str,
        notes: str | None = None,
    ) -> dict:
        """Add a verse as evidence for an entry with verification status.

        Verification: supports, contradicts, or unclear.
        Adds a location directly on the entry with verification and notes.
        """
        conn = get_connection()
        try:
            parent = conn.execute("SELECT id FROM entries WHERE id = ?", (entry_id,)).fetchone()
            if not parent:
                return {"success": False, "message": f"Entry {entry_id} not found"}

            if not verse_exists(conn, surah, ayah):
                return {"success": False, "message": f"Verse {surah}:{ayah} not found"}

            valid_verifications = ('supports', 'contradicts', 'unclear')
            if verification not in valid_verifications:
                return {"success": False, "message": f"Invalid verification. Must be one of: {', '.join(valid_verifications)}"}

            now = _now()

            # Add location with verification directly on the entry
            conn.execute(
                """INSERT OR IGNORE INTO entry_locations
                   (entry_id, surah, ayah_start, verification, notes)
                   VALUES (?, ?, ?, ?, ?)""",
                (entry_id, surah, ayah, verification,
                 notes or f"Evidence: {verification} for {surah}:{ayah}")
            )

            # Update inline counters on parent entry
            counter_col = f"verse_{verification}"
            conn.execute(
                f"UPDATE entries SET {counter_col} = COALESCE({counter_col}, 0) + 1, "
                f"verse_verified = COALESCE(verse_verified, 0) + 1, "
                f"verification_updated_at = ? WHERE id = ?",
                (now, entry_id)
            )

            confidence = _compute_confidence(conn, entry_id)
            save_database()

            return {
                "success": True,
                "message": f"Evidence added: Verse {surah}:{ayah} {verification} entry {entry_id}",
                "confidence": confidence,
            }
        except Exception as e:
            return {"success": False, "message": f"Failed to add evidence: {e}"}
