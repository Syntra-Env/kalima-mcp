"""Hermeneutics Tool: Interpretation and Semantic Consistency.

This is a thin tool layer. It queries the database, maps features to 
linguistic components using the bridge, and analyzes the consistency 
of expression.
"""

import sqlite3
import numpy as np
from typing import Any, List, Dict
from mcp.server.fastmcp import FastMCP
from ..db import get_connection
from kalima_math.gauge import (
    get_h_matrix, 
    analyze_resonance, 
    get_lyapunov_deviation, 
    get_field_tension
)
from kalima_math.root_space import concordance_distance
from ..utils.bridge import (
    build_root_vectors_for_verse,
    get_verse_word_data,
    build_root_vector_from_db,
    features_to_h_components
)
from kalima_math.verse_dynamics import analyze_verse
from ..utils.units import compose_word_text, compose_verse_text


def _get_root_instances(conn: sqlite3.Connection, root_id: int, limit: int = 500) -> list:
    """Get all morpheme instances of a root across the Quran."""
    rows = conn.execute("""
        SELECT wi.id as instance_id, wi.verse_surah, wi.verse_ayah, wi.word_index,
               wi.normalized_text, wi.word_type_id,
               mt.id as morpheme_id, mt.pos_id, mt.verb_form_id, mt.voice_id,
               mt.mood_id, mt.aspect_id, mt.person_id, mt.number_id,
               mt.gender_id, mt.case_value_id, mt.lemma_id
        FROM word_instances wi
        JOIN word_type_morphemes wtm ON wi.word_type_id = wtm.word_type_id
        JOIN morpheme_types mt ON wtm.morpheme_type_id = mt.id
        WHERE mt.root_id = ?
        ORDER BY wi.verse_surah, wi.verse_ayah, wi.word_index
        LIMIT ?
    """, (root_id, limit)).fetchall()
    return [dict(r) for r in rows]


def register(server: FastMCP):

    @server.tool()
    def analyze_root_consistency(root_feature_id: int) -> dict:
        """Analyzes the consistency of a root's usage across all its Quranic instances.

        - Low variation: meaning is conserved (consistent usage)
        - High variation: meaning evolves (context-dependent usage)
        """
        conn = get_connection()

        root_info = conn.execute(
            "SELECT lookup_key, label_ar FROM features WHERE id = ?",
            (root_feature_id,)
        ).fetchone()
        if not root_info:
            return {"error": "Root not found"}

        instances = _get_root_instances(conn, root_feature_id)
        if not instances:
            return {"error": "No instances found"}

        # Build H matrices
        h_sequence = []
        loc_strings = []
        for inst in instances:
            comps = features_to_h_components(conn, inst)
            h_sequence.append(get_h_matrix(comps))
            loc_strings.append(f"{inst['verse_surah']}:{inst['verse_ayah']}")

        # Pure math analysis
        res = analyze_resonance(h_sequence, loc_strings)

        return {
            "root": root_info['lookup_key'],
            "root_ar": root_info['label_ar'],
            "total_instances": len(instances),
            "global_variation": round(res.global_curvature, 4),
            "consistency": res.consistency,
            "hotspots": res.hotspots,
        }

    @server.tool()
    def verify_root_concordance(root_feature_id: int, proposed_meaning: str) -> dict:
        """Verify a proposed meaning for a root against ALL its Quranic instances.

        Returns instances sorted by semantic deviation (highest first).
        High-deviation instances are the potential falsifiers.
        """
        conn = get_connection()
        root_info = conn.execute(
            "SELECT lookup_key, label_ar FROM features WHERE id = ?",
            (root_feature_id,)
        ).fetchone()
        if not root_info: return {"error": "Root not found"}

        instances = _get_root_instances(conn, root_feature_id)
        
        # Compute baseline H*
        h_matrices = [get_h_matrix(features_to_h_components(conn, i)) for i in instances]
        h_star = sum(h_matrices) / len(h_matrices)

        results = []
        for i, inst in enumerate(instances):
            dev = get_lyapunov_deviation(h_matrices[i], h_star)
            results.append({
                'ref': f"{inst['verse_surah']}:{inst['verse_ayah']}",
                'word_text': inst['normalized_text'],
                'deviation': round(dev, 4),
                'verse_text': compose_verse_text(conn, inst['verse_surah'], inst['verse_ayah'])[:120],
            })

        results.sort(key=lambda x: x['deviation'], reverse=True)

        return {
            "root": root_info['lookup_key'],
            "meaning": proposed_meaning,
            "instances": results,
            "note": "High-deviation instances are priorities for falsification."
        }

    @server.tool()
    def compare_with_traditional(surah: int, ayah: int) -> dict:
        """Compare Scholar research entries with traditional interpretations for a verse."""
        conn = get_connection()
        verse_text = compose_verse_text(conn, surah, ayah)
        
        trad = [dict(r) for r in conn.execute(
            "SELECT source, interpretation FROM traditional_interpretations WHERE surah=? AND ayah=?", 
            (surah, ayah)).fetchall()]

        word_data = get_verse_word_data(conn, surah, ayah)
        root_vectors = build_root_vectors_for_verse(conn, surah, ayah)
        analysis = analyze_verse(word_data, root_vectors)

        return {
            "ref": f"{surah}:{ayah}",
            "text": verse_text,
            "traditional": trad,
            "emphasis": analysis.emphasis
        }

    @server.tool()
    def measure_root_similarity(root_feature_id_a: int, root_feature_id_b: int) -> dict:
        """Calculate the semantic similarity between two roots based on their distribution."""
        conn = get_connection()
        rv_a = build_root_vector_from_db(conn, root_feature_id_a)
        rv_b = build_root_vector_from_db(conn, root_feature_id_b)
        
        if not rv_a or not rv_b: return {"error": "Root not found"}
        
        return {
            "root_a": rv_a.lookup_key,
            "root_b": rv_b.lookup_key,
            "distance": round(concordance_distance(rv_a, rv_b), 4),
            "cooccurrence": rv_a.cooccurrence_counts.get(root_feature_id_b, 0)
        }
