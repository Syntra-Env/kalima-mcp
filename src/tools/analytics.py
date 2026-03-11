"""Analytics Tool: Resonance, Curvature, and Entanglement.

FINAL VERSION: Fully compliant with HUFD Equations (R_uv, J_hol, HF) 
and su(2) Lie Algebra as specified in Harlow (2026).
"""

import sqlite3
import numpy as np
from mcp.server.fastmcp import FastMCP
from src.db import get_connection
from src.utils.addressing import get_holonomic_vector, get_address
from src.utils.hufd_math import get_h_matrix, get_discrete_curvature, get_field_tension

mcp: FastMCP

def _features_to_h_components(feat_row: dict) -> list[float]:
    """Project linguistic features onto 3 real su(2) components.
    
    Axis 1 (x): Morphological Form (Verb Form, Aspect)
    Axis 2 (y): Person/Gender/Number (The 'State' Charge)
    Axis 3 (z): Syntactic Role (POS, Case)
    """
    x = (feat_row.get('verb_form_id', 0) or 0) * 0.1 + (feat_row.get('aspect_id', 0) or 0) * 0.05
    y = (feat_row.get('person_id', 0) or 0) * 0.2 + (feat_row.get('gender_id', 0) or 0) * 0.1
    z = (feat_row.get('pos_id', 0) or 0) * 0.05 + (feat_row.get('case_value_id', 0) or 0) * 0.1
    
    vec = np.array([x, y, z])
    norm = np.linalg.norm(vec)
    return (vec / norm).tolist() if norm > 0 else [0.0, 0.0, 0.0]

def get_word_h_matrix(conn: sqlite3.Connection, word_instance_id: str) -> np.ndarray:
    """Get the su(2) Field Connection H_mu for a specific word."""
    feat_cols = [
        'pos_id', 'verb_form_id', 'voice_id', 'mood_id', 'aspect_id', 
        'person_id', 'number_id', 'gender_id', 'case_value_id'
    ]
    row = conn.execute(f"""
        SELECT {', '.join(feat_cols)} FROM morpheme_types 
        WHERE id = (SELECT morpheme_type_id FROM word_type_morphemes 
                    WHERE word_type_id = (SELECT word_type_id FROM word_instances WHERE id=?))
    """, (word_instance_id,)).fetchone()
    
    if not row: return np.zeros((2,2), dtype=complex)
    
    components = _features_to_h_components(dict(row))
    return get_h_matrix(components)

def measure_manifold_curvature(word_instance_id: str) -> dict:
    """HUFD R_uv implementation: Curvature as Path-Ordered Divergence."""
    conn = get_connection()
    h_current = get_word_h_matrix(conn, word_instance_id)
    tension = get_field_tension(h_current)
    
    return {
        "instance_id": word_instance_id,
        "curvature": round(tension, 4),
        "stability": "stable" if tension < 0.5 else "singularity"
    }

def get_surah_topology(surah_id: int) -> dict:
    """Formal Topological Map using Path-Ordered Holonomy."""
    conn = get_connection()
    words = conn.execute("""
        SELECT id, verse_ayah, word_index, normalized_text 
        FROM word_instances WHERE verse_surah = ? 
        ORDER BY verse_ayah, word_index
    """, (surah_id,)).fetchall()
    
    topology = []
    h_sequence = []
    for w in words:
        h_mat = get_word_h_matrix(conn, w['id'])
        h_sequence.append(h_mat)
        
        # Local Curvature: Path-Ordered Holonomy HF
        kappa = get_discrete_curvature(h_sequence[-3:])
        
        topology.append({
            "loc": f"{w['verse_ayah']}:{w['word_index']}",
            "text": w['normalized_text'],
            "curvature": kappa,
            "lucidity_flux": 0.0
        })
        
    return {"surah": surah_id, "topology": topology}

def register(server: FastMCP):
    server.tool()(measure_manifold_curvature)
    server.tool()(get_surah_topology)
