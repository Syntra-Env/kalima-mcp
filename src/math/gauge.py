"""Abjadic Gauge Field: su(2) Lie Algebra and Holonomy.

Implements the physical foundation for Quranic research:
  - su(2) generators (Pauli matrices)
  - Field connection H_mu
  - Curvature tensor R_uv = [H_u, H_v]
  - Holonomic closure ∮H_μ dx^μ
  - Lyapunov deviation (tension)
"""

import numpy as np
from scipy.linalg import expm
from dataclasses import dataclass

# Pauli Matrices: The basis for the su(2) gauge field
SIGMA_1 = np.array([[0, 1], [1, 0]], dtype=complex)
SIGMA_2 = np.array([[0, -1j], [1j, 0]], dtype=complex)
SIGMA_3 = np.array([[1, 0], [0, -1]], dtype=complex)
SIGMAS = [SIGMA_1, SIGMA_2, SIGMA_3]


@dataclass
class ResonanceAnalysis:
    """Holonomic resonance analysis for a root or sequence."""
    global_curvature: float
    consistency: str  # highly_consistent, moderately_consistent, context_dependent
    hotspots: list[dict]  # high-curvature windows


def get_h_matrix(components: list[float]) -> np.ndarray:
    """Build su(2) matrix from components [x, y, z]."""
    if len(components) < 3:
        return np.zeros((2, 2), dtype=complex)
    return sum(components[a] * 1j * SIGMAS[a] / 2 for a in range(3))


def calculate_curvature_tensor(h_mu: np.ndarray, h_nu: np.ndarray) -> np.ndarray:
    """Compute Curvature Tensor R_uv = [H_u, H_v].
    
    In the discrete sequence, this represents the structural tension 
    between two adjacent word field connections.
    """
    return h_mu @ h_nu - h_nu @ h_mu


def get_discrete_curvature(h_sequence: list[np.ndarray]) -> float:
    """Compute the holonomic curvature (angle) for a sequence of su(2) matrices.
    
    Uses the trace of the ordered product (parallel transport).
    """
    if not h_sequence:
        return 0.0
    hf = np.eye(2, dtype=complex)
    for h in h_sequence:
        hf = hf @ expm(h)
    w = np.real(hf[0, 0])
    w = np.clip(np.abs(w), 0.0, 1.0)
    return float(2 * np.arccos(w))


def get_field_tension(h_matrix: np.ndarray) -> float:
    """Compute the field tension/energy: Tr(H†H)."""
    return float(np.real(np.trace(h_matrix.conj().T @ h_matrix)))


def get_lyapunov_deviation(h_state: np.ndarray, h_baseline: np.ndarray) -> float:
    """Compute the deviation (tension) between a local state and a baseline.
    
    Used to find 'meaning shifts' where a word instance deviates from 
    its root's typical geometric profile.
    """
    diff = h_state - h_baseline
    return get_field_tension(diff)


def analyze_resonance(h_sequence: list[np.ndarray], locations: list[str]) -> ResonanceAnalysis:
    """Analyze the holonomic consistency of a field sequence."""
    global_kappa = get_discrete_curvature(h_sequence)

    # Local curvatures (sliding window)
    local_curvatures = []
    for i in range(len(h_sequence) - 4):
        window = h_sequence[i:i+5]
        kappa = get_discrete_curvature(window)
        local_curvatures.append({
            'start': locations[i],
            'end': locations[i+4],
            'curvature': float(kappa),
        })

    hotspots = sorted(local_curvatures, key=lambda x: x['curvature'], reverse=True)[:10]

    if global_kappa < 0.5:
        consistency = "highly_consistent"
    elif global_kappa < 1.5:
        consistency = "moderately_consistent"
    else:
        consistency = "context_dependent"

    return ResonanceAnalysis(
        global_curvature=float(global_kappa),
        consistency=consistency,
        hotspots=hotspots
    )
