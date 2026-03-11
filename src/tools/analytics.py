"""Analytics Tool: Resonance, Curvature, and Entanglement.

FINAL VERSION: Fully compliant with HUFD Equations (R_uv, J_hol, HF) 
and su(2) Lie Algebra as specified in Harlow (2026).
"""

import sqlite3
import numpy as np
from mcp.server.fastmcp import FastMCP
from src.db import get_connection
from src.utils.addressing import get_holonomic_vector, get_address
from src.math.holonomy import get_h_matrix, get_discrete_curvature, get_field_tension
from src.math.bridge import features_to_h_components

mcp: FastMCP

def get_word_h_matrix(conn: sqlite3.Connection, word_instance_id: str) -> np.ndarray:
    """Get the high-resolution su(2) Field Connection H_mu."""
    feat_cols = [
        'root_id', 'pos_id', 'verb_form_id', 'voice_id', 'mood_id', 'aspect_id', 
        'person_id', 'number_id', 'gender_id', 'case_value_id'
    ]
    row = conn.execute(f"""
        SELECT {', '.join(feat_cols)}, mt.id as mt_id FROM morpheme_types mt
        JOIN word_type_morphemes wtm ON wtm.morpheme_type_id = mt.id
        JOIN word_instances wi ON wi.word_type_id = wtm.word_type_id
        WHERE wi.id = ?
    """, (word_instance_id,)).fetchone()
    
    if not row: return np.zeros((2,2), dtype=complex)
    
    # Fetch root UOR address for coupling
    root_addr = get_address(conn, 'root', str(row['root_id']))
    
    components = features_to_h_components(conn, dict(row), root_addr)
    return get_h_matrix(components)

def measure_manifold_curvature(word_instance_id: str) -> dict:
    """HUFD R_uv implementation: Curvature as Field Tension."""
    conn = get_connection()
    h_current = get_word_h_matrix(conn, word_instance_id)
    tension = get_field_tension(h_current)
    
    return {
        "instance_id": word_instance_id,
        "curvature": round(tension, 4),
        "stability": "stable" if tension < 5.0 else "singularity"
    }

def get_surah_topology(surah_id: int) -> dict:
    """High-Fidelity Topological Map."""
    conn = get_connection()
    words = conn.execute("""
        SELECT id, verse_ayah, word_index, normalized_text 
        FROM word_instances WHERE verse_surah = ? 
        ORDER BY verse_ayah, word_index
    """, (surah_id,)).fetchall()
    
    topology = []
    h_sequence = []
    prev_curvature = 0.0
    
    for w in words:
        h_mat = get_word_h_matrix(conn, w['id'])
        h_sequence.append(h_mat)
        
        kappa = get_discrete_curvature(h_sequence[-3:])
        
        topology.append({
            "loc": f"{w['verse_ayah']}:{w['word_index']}",
            "text": w['normalized_text'],
            "curvature": kappa,
            "lucidity_flux": round(prev_curvature - kappa, 4)
        })
        prev_curvature = kappa
        
    return {"surah": surah_id, "topology": topology}

def compute_topology(addresses: list[str]) -> dict:
    """Compute topological Betti numbers for a set of UOR addresses."""
    from src.utils.topology import get_constraints_topology
    from src.db import get_connection
    conn = get_connection()
    return get_constraints_topology(conn, addresses)

def compute_uor_index(addresses: list[str]) -> dict:
    """Compute UOR Index Theorem metrics for a set of UOR addresses."""
    from src.utils.topology import compute_uor_index as uor_index
    from src.db import get_connection
    conn = get_connection()
    return uor_index(conn, addresses)

def register(server: FastMCP):
    server.tool()(measure_manifold_curvature)
    server.tool()(get_surah_topology)
    server.tool()(compute_topology)
    server.tool()(compute_uor_index)
