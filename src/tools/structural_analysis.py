"""Structural Analysis Tool: Tension, Topology, and Structural Mapping.

Applies analytical methods to uncover the structural properties of the text.
"""

import sqlite3
import numpy as np
from mcp.server.fastmcp import FastMCP
from src.db import get_connection
from src.utils.addressing import get_holonomic_vector, get_address
from geometer.gauge import get_h_matrix, get_discrete_curvature, get_field_tension
from src.utils.bridge import features_to_h_components

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

def measure_structural_tension(word_instance_id: str) -> dict:
    """Measures the structural tension on a single word instance."""
    conn = get_connection()
    h_current = get_word_h_matrix(conn, word_instance_id)
    tension = get_field_tension(h_current)
    
    return {
        "instance_id": word_instance_id,
        "tension": round(tension, 4),
        "interpretation": "stable" if tension < 5.0 else "high-energy"
    }

def map_surah_structure(surah_id: int) -> dict:
    """Creates a high-fidelity structural map of a surah."""
    conn = get_connection()
    words = conn.execute("""
        SELECT id, verse_ayah, word_index, normalized_text 
        FROM word_instances WHERE verse_surah = ? 
        ORDER BY verse_ayah, word_index
    """, (surah_id,)).fetchall()
    
    structure = []
    h_sequence = []
    prev_value = 0.0
    
    for w in words:
        h_mat = get_word_h_matrix(conn, w['id'])
        h_sequence.append(h_mat)
        
        kappa = get_discrete_curvature(h_sequence[-3:])
        
        structure.append({
            "loc": f"{w['verse_ayah']}:{w['word_index']}",
            "text": w['normalized_text'],
            "value": kappa,
            "flux": round(prev_value - kappa, 4)
        })
        prev_value = kappa
        
    return {"surah": surah_id, "structure": structure}

def compute_topology(addresses: list[str]) -> dict:
    """Compute topological properties for a set of UOR addresses."""
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
    server.tool()(measure_structural_tension)
    server.tool()(map_surah_structure)
    server.tool()(compute_topology)
    server.tool()(compute_uor_index)
