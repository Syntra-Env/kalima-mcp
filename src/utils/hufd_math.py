"""HUFD Mathematical Core.

Implements su(2) basis, Pauli matrices, and Curvature Tensors 
as specified in 'hufd-equations.pdf'.
"""

import numpy as np
from scipy.linalg import expm

# Pauli Matrices (Section 2.4, Eq 10)
SIGMA_1 = np.array([[0, 1], [1, 0]], dtype=complex)
SIGMA_2 = np.array([[0, -1j], [1j, 0]], dtype=complex)
SIGMA_3 = np.array([[1, 0], [0, -1]], dtype=complex)
SIGMAS = [SIGMA_1, SIGMA_2, SIGMA_3]

def get_h_matrix(components: list[float]) -> np.ndarray:
    """Build su(2) matrix from 3 real components (Section 2.4, Eq 9).
    
    H_mu = sum( H^a_mu * i * sigma_a / 2 )
    """
    comp = components[:3] + [0.0] * (3 - len(components))
    h_mat = sum(comp[a] * 1j * SIGMAS[a] / 2 for a in range(3))
    return h_mat

def calculate_curvature_tensor(h_mu: np.ndarray, h_nu: np.ndarray) -> np.ndarray:
    """Compute Curvature Tensor R_uv (Section 2.1, Eq 7/8).
    
    R_uv = [H_mu, H_nu] + background_term (simplified here to 0 for text)
    """
    return h_mu @ h_nu - h_nu @ h_mu

def get_discrete_curvature(h_sequence: list[np.ndarray]) -> float:
    """Calculate Curvature kappa from a sequence of connections (Section 8, Eq 30).
    
    kappa = 2 * arccos(|w|) where w is the scalar part of the holonomy.
    """
    if not h_sequence: return 0.0
    
    hf = np.eye(2, dtype=complex)
    for h in h_sequence:
        hf = hf @ expm(h)
        
    w = np.real(hf[0, 0])
    w = np.clip(np.abs(w), 0.0, 1.0)
    kappa = 2 * np.arccos(w)
    return float(kappa)

def get_field_tension(h_matrix: np.ndarray) -> float:
    """The self-interaction energy Tr(R_uv R^uv) proxy for a single node."""
    r_sq = h_matrix @ h_matrix
    return float(np.abs(np.trace(r_sq)))
