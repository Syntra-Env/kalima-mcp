"""
Gauge Field Standards
=====================

Axioms defining the SU(2) Lie algebra and holonomy implementation.
These are the formal rules that the geometer.gauge module MUST satisfy.
"""

import numpy as np

# SU(2) Lie Algebra Parameters
LIE_ALGEBRA_DIMENSION: int = 3       # SU(2) has 3 generators
MATRIX_DIMENSION: int = 2            # SU(2) matrices are 2x2
COMPLEX_TYPE: np.dtype = np.complex128

# Pauli Matrix Properties (Generators of SU(2))
PAULI_NAMES: list[str] = ["σ₁", "σ₂", "σ₃"]
PAULI_INDEX: dict[str, int] = {"σ₁": 0, "σ₂": 1, "σ₃": 2}

# Pauli Matrix Trace Properties
# Tr(σᵢ) = 0 for all i
PAULI_TRACE_ZERO: bool = True

# Pauli Matrix Anti-commutation
# {σᵢ, σⱼ} = 2δᵢⱼI
KRONECKER_DELTA_PROPERTY: bool = True

# Pauli Matrix Commutation
# [σᵢ, σⱼ] = 2iεᵢⱼₖσₖ (Levi-Civita symbol)
LEVICIVITA_SU2: bool = True

# Bounds
METRIC_BOUNDS: dict[str, tuple[float, float]] = {
    "curvature": (0.0, np.pi),           # Holonomic curvature ∈ [0, π]
    "field_tension": (0.0, float('inf')), # Tension is non-negative
    "lyapunov_deviation": (0.0, float('inf')),  # Deviation is non-negative
}

# Consistency Levels
CONSISTENCY_LEVELS: list[str] = [
    "highly_consistent",
    "moderately_consistent",
    "context_dependent",
]

# Curvature Thresholds (from analyze_resonance)
HIGHLY_CONSISTENT_MAX: float = 0.5
MODERATELY_CONSISTENT_MAX: float = 1.5
# > 1.5 is context_dependent

# Holonomy Requirements
# Parallel transport around closed loop should give valid rotation
HOLONOMY_PROPERTIES: dict[str, object] = {
    "trace_bounded": True,      # |Tr(H)| <= 2 for SU(2)
    "unitarity": True,          # H†H = I
    "determinant_one": True,    # det(H) = 1
}

# Field Matrix Constraints
FIELD_MATRIX_CONSTRAINTS: dict[str, object] = {
    "anti_hermitian": True,     # H = -H† for SU(2) generators
    "dimension": (2, 2),
    "complex": True,
}

# Resonance Analysis Requirements
RESONANCE_REQUIRED_FIELDS: list[str] = [
    "global_curvature",
    "consistency",
    "hotspots",
]

HOTSPOT_COUNT: int = 10  # Top 10 high-curvature windows

# Component Bounds for H Matrix Construction
COMPONENT_RANGE: tuple[float, float] = (-float('inf'), float('inf'))  # No intrinsic bound

# Exponential Map Requirements
# exp(H) should be unitary for anti-Hermitian H
EXPONENTIAL_MAP_VALID: bool = True
