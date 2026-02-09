"""Verse context tool: morphology-aware claim lookup per word."""

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
        include_root_claims: bool = True,
        include_form_claims: bool = True,
        include_pos_claims: bool = True,
    ) -> dict:
        """Get a verse with morphology-aware claim context.

        For each word, surfaces related claims based on its root, verb form,
        and POS from the pattern_linguistic_features table.
        """
        conn = get_connection()

        # Get the verse text
        verse_row = conn.execute(
            "SELECT surah_number, ayah_number, text FROM verse_texts WHERE surah_number = ? AND ayah_number = ?",
            (surah, ayah)
        ).fetchone()

        if not verse_row:
            return {"error": f"Verse {surah}:{ayah} not found"}

        verse = dict(verse_row)

        # Get all tokens and their segments for this verse
        tokens = conn.execute(
            """SELECT
                t.id as token_id,
                t.text as token_text,
                t.token_index,
                s.root,
                s.lemma,
                s.pos,
                s.verb_form,
                s.aspect,
                s.mood
            FROM tokens t
            LEFT JOIN segments s ON s.token_id = t.id
            WHERE t.verse_surah = ? AND t.verse_ayah = ?
            ORDER BY t.token_index ASC""",
            (surah, ayah)
        ).fetchall()

        # For each token, find related claims based on linguistic features
        words_with_context = []

        for token in tokens:
            related_claims = []

            features_to_check = []
            if include_root_claims and token['root']:
                features_to_check.append(('root', token['root']))
            if include_form_claims and token['verb_form']:
                features_to_check.append(('verb_form', token['verb_form']))
            if include_pos_claims and token['pos']:
                features_to_check.append(('pos', token['pos']))
            if token['aspect']:
                features_to_check.append(('aspect', token['aspect']))

            for feat_type, feat_value in features_to_check:
                claims = conn.execute(
                    """SELECT DISTINCT
                        c.id as claim_id,
                        c.content as claim_content,
                        c.phase as claim_phase,
                        c.pattern_id,
                        plf.feature_type as matched_feature_type,
                        plf.feature_value as matched_feature_value
                    FROM pattern_linguistic_features plf
                    JOIN claims c ON c.pattern_id = plf.pattern_id
                    WHERE plf.feature_type = ? AND plf.feature_value = ?""",
                    (feat_type, feat_value)
                ).fetchall()
                related_claims.extend(dict(c) for c in claims)

            words_with_context.append({
                "token_text": token['token_text'],
                "token_index": token['token_index'],
                "root": token['root'],
                "lemma": token['lemma'],
                "pos": token['pos'],
                "verb_form": token['verb_form'],
                "aspect": token['aspect'],
                "related_claims": related_claims,
            })

        # Get direct verse claims
        direct_claims = conn.execute(
            """SELECT
                vc.claim_id,
                c.content as claim_content,
                c.phase as claim_phase,
                vc.evidence_type
            FROM verse_claims vc
            JOIN claims c ON c.id = vc.claim_id
            WHERE vc.surah = ? AND vc.ayah = ?
            ORDER BY vc.created_at DESC""",
            (surah, ayah)
        ).fetchall()

        return {
            "verse": verse,
            "words_with_context": words_with_context,
            "direct_verse_claims": [dict(c) for c in direct_claims],
        }
