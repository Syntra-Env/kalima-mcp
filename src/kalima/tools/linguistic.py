"""Linguistic analysis tools: morphological search, pattern creation, evidence."""

import json
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from ..db import get_connection, save_database, invalidate_graph_cache
from ..utils.short_id import generate_pattern_id, generate_claim_id, generate_evidence_id

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
    ) -> list[dict]:
        """Search verses by linguistic features like part of speech, verb form, mood, aspect, root, etc."""
        conn = get_connection()

        # Build WHERE clause dynamically
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
                conditions.append(f"s.{key} = ?")
                params.append(normalized)

        if surah is not None:
            conditions.append("t.verse_surah = ?")
            params.append(surah)

        if not conditions:
            return [{"error": "At least one linguistic feature must be specified"}]

        where_clause = " AND ".join(conditions)
        params.append(limit)

        # Get matching verses
        verse_rows = conn.execute(
            f"""SELECT DISTINCT
                t.verse_surah AS surah_number,
                t.verse_ayah AS ayah_number,
                vt.text
            FROM segments s
            JOIN tokens t ON s.token_id = t.id
            JOIN verse_texts vt ON t.verse_surah = vt.surah_number AND t.verse_ayah = vt.ayah_number
            WHERE {where_clause}
            ORDER BY t.verse_surah ASC, t.verse_ayah ASC
            LIMIT ?""",
            params
        ).fetchall()

        # For each verse, fetch tokens and segments
        results = []
        for verse in verse_rows:
            v = dict(verse)

            tokens = conn.execute(
                "SELECT * FROM tokens WHERE verse_surah = ? AND verse_ayah = ? ORDER BY token_index ASC",
                (v['surah_number'], v['ayah_number'])
            ).fetchall()

            segments = conn.execute(
                """SELECT s.* FROM segments s
                   JOIN tokens t ON s.token_id = t.id
                   WHERE t.verse_surah = ? AND t.verse_ayah = ?
                   ORDER BY t.token_index ASC""",
                (v['surah_number'], v['ayah_number'])
            ).fetchall()

            v['tokens'] = [dict(t) for t in tokens]
            v['segments'] = [dict(s) for s in segments]
            results.append(v)

        return results

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
        """
        conn = get_connection()
        try:
            pid = generate_pattern_id(conn)
            now = _now()

            conn.execute(
                "INSERT INTO patterns (id, description, pattern_type, scope, phase, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pid, description, pattern_type, scope, phase, now, now)
            )

            # Store linguistic features
            if linguistic_features and isinstance(linguistic_features, dict):
                for feat_type, feat_value in linguistic_features.items():
                    if feat_value is not None:
                        feat_id = f"feat_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{id(feat_type) % 100000}"
                        conn.execute(
                            "INSERT INTO pattern_linguistic_features (id, pattern_id, feature_type, feature_value, created_at) VALUES (?, ?, ?, ?, ?)",
                            (feat_id, pid, feat_type, str(feat_value), now)
                        )

            # Create a linked claim
            cid = generate_claim_id(conn)
            claim_content = f"{description}\n\nInterpretation: {interpretation}"
            if linguistic_features:
                claim_content += f"\n\nLinguistic features: {json.dumps(linguistic_features)}"

            conn.execute(
                "INSERT INTO claims (id, content, phase, pattern_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (cid, claim_content, phase, pid, now, now)
            )

            save_database()
            invalidate_graph_cache()

            return {
                "success": True,
                "pattern_id": pid,
                "claim_id": cid,
                "message": f"Pattern created successfully with ID: {pid}\nLinked claim: {cid}",
            }
        except Exception as e:
            return {"success": False, "pattern_id": "", "claim_id": "", "message": f"Failed to create pattern: {e}"}

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
            surah_row = conn.execute("SELECT name FROM surahs WHERE number = ?", (surah,)).fetchone()
            surah_name = surah_row['name'] if surah_row else f"Surah {surah}"

            cid = generate_claim_id(conn)
            now = _now()

            claim_content = f"Surah {surah} ({surah_name}) - Theme: {theme}"
            if description:
                claim_content += f"\n\nDescription: {description}"

            conn.execute(
                "INSERT INTO claims (id, content, phase, pattern_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (cid, claim_content, phase, None, now, now)
            )

            save_database()
            invalidate_graph_cache()

            return {
                "success": True,
                "claim_id": cid,
                "message": f"Surah theme created successfully for {surah_name}\nClaim ID: {cid}\nPhase: {phase}",
            }
        except Exception as e:
            return {"success": False, "claim_id": "", "message": f"Failed to create surah theme: {e}"}

    @mcp.tool()
    def add_verse_evidence(
        claim_id: str,
        surah: int,
        ayah: int,
        verification: str,
        notes: str | None = None,
    ) -> dict:
        """Add a verse as evidence for a claim with verification status.

        Verification: supports, contradicts, or unclear.
        """
        conn = get_connection()
        try:
            if not conn.execute("SELECT id FROM claims WHERE id = ?", (claim_id,)).fetchone():
                return {"success": False, "evidence_id": "", "message": f"Claim {claim_id} not found"}

            if not conn.execute("SELECT * FROM verse_texts WHERE surah_number = ? AND ayah_number = ?", (surah, ayah)).fetchone():
                return {"success": False, "evidence_id": "", "message": f"Verse {surah}:{ayah} not found"}

            eid = generate_evidence_id(conn)
            now = _now()

            evidence_notes = f"[{verification.upper()}] {notes or ''}".strip()

            conn.execute(
                "INSERT INTO claim_evidence (id, claim_id, surah, ayah, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (eid, claim_id, surah, ayah, evidence_notes, now)
            )

            save_database()
            invalidate_graph_cache()

            return {
                "success": True,
                "evidence_id": eid,
                "message": f"Evidence added: Verse {surah}:{ayah} {verification} claim {claim_id}",
            }
        except Exception as e:
            return {"success": False, "evidence_id": "", "message": f"Failed to add evidence: {e}"}
