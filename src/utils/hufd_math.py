"""HUFD Mathematical Core.

UPGRADED: High-Resolution Lexical Coupling.
Incorporates Root Identity (UOR) into the field connection H_mu.
"""

import numpy as np
from scipy.linalg import expm
import math
import sqlite3

# Pauli Matrices
SIGMA_1 = np.array([[0, 1], [1, 0]], dtype=complex)
SIGMA_2 = np.array([[0, -1j], [1j, 0]], dtype=complex)
SIGMA_3 = np.array([[1, 0], [0, -1]], dtype=complex)
SIGMAS = [SIGMA_1, SIGMA_2, SIGMA_3]

_surprisal_cache: dict[int, float] = {}

def _get_surprisal(conn: sqlite3.Connection, feature_id: int | None) -> float:
    if feature_id is None: return 0.0
    if feature_id in _surprisal_cache: return _surprisal_cache[feature_id]
    row = conn.execute("SELECT frequency FROM features WHERE id = ?", (feature_id,)).fetchone()
    if not row or not row['frequency'] or row['frequency'] <= 0:
        _surprisal_cache[feature_id] = 0.0
        return 0.0
    val = math.log(max(128000 / row['frequency'], 1.0))
    _surprisal_cache[feature_id] = val
    return val

def _address_to_component(address: str | None) -> float:
    """Project a hex UOR address onto a real scalar [-1, 1]."""
    if not address: return 0.0
    seed = int(address[:8], 16)
    return (seed / 0xFFFFFFFF) * 2.0 - 1.0

# Global metric cache
_g_metric = np.eye(3)

def compute_information_geometric_metric(conn: sqlite3.Connection, sample_size: int = 1000):
    """Build full information-geometric metric g_mu_nu from feature co-occurrence."""
    global _g_metric
    
    # Sample some morpheme types to compute covariance
    rows = conn.execute("""
        SELECT root_id, lemma_id, pos_id, verb_form_id, voice_id, mood_id, aspect_id,
               person_id, number_id, gender_id, case_value_id
        FROM morpheme_types
        LIMIT ?
    """, (sample_size,)).fetchall()
    
    data = []
    for r in rows:
        # Compute raw components without scaling or metric
        x = (_get_surprisal(conn, r['root_id']) + _get_surprisal(conn, r['lemma_id']))
        y = (_get_surprisal(conn, r['verb_form_id']) + _get_surprisal(conn, r['aspect_id']) +
             _get_surprisal(conn, r['person_id']) + _get_surprisal(conn, r['gender_id']) +
             _get_surprisal(conn, r['number_id']))
        z = (_get_surprisal(conn, r['pos_id']) + _get_surprisal(conn, r['case_value_id']) +
             _get_surprisal(conn, r['voice_id']) + _get_surprisal(conn, r['mood_id']))
        data.append([x, y, z])
    
    if not data:
        _g_metric = np.eye(3)
        return
        
    data = np.array(data)
    cov = np.cov(data.T)
    
    # Information-geometric metric is the inverse covariance (Fisher metric for Gaussian)
    try:
        # Add small regularization to ensure invertibility
        _g_metric = np.linalg.inv(cov + np.eye(3) * 1e-6)
    except np.linalg.LinAlgError:
        _g_metric = np.eye(3)

def features_to_h_components(conn: sqlite3.Connection, feat_row: dict, root_addr: str | None = None) -> list[float]:
    """High-Resolution Mapping: Semantic + Morphological + Syntactic."""
    SCALE = 0.1 # Numerical stability for su(2) exponentials
    
    raw_x = (_get_surprisal(conn, feat_row.get('root_id')) + 
             _get_surprisal(conn, feat_row.get('lemma_id')))
    
    if root_addr:
        raw_x += _address_to_component(root_addr)
        
    raw_y = (_get_surprisal(conn, feat_row.get('verb_form_id')) + 
             _get_surprisal(conn, feat_row.get('aspect_id')) +
             _get_surprisal(conn, feat_row.get('person_id')) +
             _get_surprisal(conn, feat_row.get('gender_id')) +
             _get_surprisal(conn, feat_row.get('number_id')))
             
    raw_z = (_get_surprisal(conn, feat_row.get('pos_id')) + 
             _get_surprisal(conn, feat_row.get('case_value_id')) +
             _get_surprisal(conn, feat_row.get('voice_id')) +
             _get_surprisal(conn, feat_row.get('mood_id')))
    
    raw_vec = np.array([raw_x, raw_y, raw_z])
    
    # Apply the metric: V_metric = g_mu_nu * V_raw
    # (Actually it should be a whitening transform, but g_mu_nu is the metric)
    metric_vec = _g_metric @ raw_vec
    
    return (metric_vec * SCALE).tolist()

def get_h_matrix(components: list[float]) -> np.ndarray:
    return sum(components[a] * 1j * SIGMAS[a] / 2 for a in range(3))

def calculate_curvature_tensor(h_mu: np.ndarray, h_nu: np.ndarray, background_omega: np.ndarray = None) -> np.ndarray:
    """Compute Curvature Tensor R_uv = [H_u, H_v] + omega_[u eta_v].
    
    In the discrete sequence, this represents the structural tension 
    between two adjacent word field connections.
    """
    # Commutator [H_u, H_v]
    commutator = h_mu @ h_nu - h_nu @ h_mu
    
    if background_omega is None:
        # Default background term derived from the Pauli algebra (torsion-free)
        # Using a small identity coupling as background curvature
        background_omega = np.eye(2, dtype=complex) * 1e-4
        
    return commutator + background_omega

def get_discrete_curvature(h_sequence: list[np.ndarray]) -> float:
    if not h_sequence: return 0.0
    hf = np.eye(2, dtype=complex)
    for h in h_sequence:
        hf = hf @ expm(h)
    w = np.real(hf[0, 0])
    w = np.clip(np.abs(w), 0.0, 1.0)
    return float(2 * np.arccos(w))

def get_field_tension(h_matrix: np.ndarray) -> float:
    # Tr(R^2) where R ~ H in the local frame
    # Normalized curvature energy
    return float(np.real(np.trace(h_matrix.conj().T @ h_matrix)))
