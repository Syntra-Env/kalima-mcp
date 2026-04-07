"""
Abjadic Gauge Field: PRISM-Native su(2) Lie Algebra and Holonomy.

This module extends PRISM with SU(2) gauge field operations for Quranic analysis:
  - su(2) generators (Pauli matrices)
  - Field connection H_mu encoded as PRISM coordinates
  - Curvature tensor R_uv = [H_u, H_v] with PRISM derivation
  - Holonomic closure with PRISM correlation
  - Lyapunov deviation using PRISM fidelity
"""

from dataclasses import dataclass
from typing import Optional

from .prism import UOR
from .uor import Q256


# ── PRISM Quantum for Gauge Fields ──────────────────────────────────────────
# Quantum 0 = 8 bits per gauge component = enough for float precision
GAUGE_QUANTUM = 0
GAUGE_ENGINE = UOR(quantum=GAUGE_QUANTUM)

# ── Pauli Matrices: The basis for the su(2) gauge field ──────────────────
# These remain numpy-based for matrix operations, but PRISM is used for
# coordinate encoding and correlation of field states

SIGMA_1 = [[0, 1], [1, 0]]
SIGMA_2 = [[0, -1j], [1j, 0]]
SIGMA_3 = [[1, 0], [0, -1]]
SIGMAS = [SIGMA_1, SIGMA_2, SIGMA_3]


@dataclass
class ResonanceAnalysis:
    """Holonomic resonance analysis for a root or sequence."""
    global_curvature: float
    consistency: str
    hotspots: list
    prism_correlation: Optional[dict] = None
    derivation_id: Optional[str] = None


@dataclass
class FieldState:
    """A field state with PRISM coordinate representation."""
    components: tuple  # (x, y, z) as integers (PRISM-ready)
    matrix: list  # Complex 2x2 matrix
    
    @property
    def prism_coordinate(self) -> tuple:
        """Encode field state as PRISM coordinate."""
        return GAUGE_ENGINE._to_bytes(
            (self.components[0] & 0xFF) |
            ((self.components[1] & 0xFF) << 8) |
            ((self.components[2] & 0xFF) << 16)
        )
    
    @property
    def prism_triplet(self):
        """PRISM triadic coordinate for this field state."""
        return GAUGE_ENGINE.triad(self.prism_coordinate)
    
    @property
    def stratum(self) -> int:
        """Information content of this field state."""
        return self.prism_triplet.total_stratum


def _to_complex_matrix(components: list) -> list:
    """Build complex 2x2 matrix from components [x, y, z]."""
    if len(components) < 3:
        return [[0, 0], [0, 0]]
    x, y, z = float(components[0]), float(components[1]), float(components[2])
    return [
        [1j * z / 2, 1j * (x - 1j * y) / 2],
        [1j * (x + 1j * y) / 2, -1j * z / 2]
    ]


def get_h_matrix(components: list) -> list:
    """Build su(2) matrix from components [x, y, z]."""
    return _to_complex_matrix(components)


def get_field_state(components: list) -> FieldState:
    """Create a FieldState with PRISM coordinates from components."""
    if len(components) < 3:
        comp = (0, 0, 0)
    else:
        comp = (int(components[0]), int(components[1]), int(components[2]))
    
    matrix = _to_complex_matrix(components)
    return FieldState(components=comp, matrix=matrix)


def calculate_curvature_tensor(h_mu: list, h_nu: list) -> list:
    """Compute Curvature Tensor R_uv = [H_u, H_v].
    
    In the discrete sequence, this represents the structural tension 
    between two adjacent word field connections.
    """
    # Matrix commutation: R = HμHν - HνHμ
    def mat_mul(a, b):
        return [
            [a[0][0]*b[0][0] + a[0][1]*b[1][0], a[0][0]*b[0][1] + a[0][1]*b[1][1]],
            [a[1][0]*b[0][0] + a[1][1]*b[1][0], a[1][0]*b[0][1] + a[1][1]*b[1][1]]
        ]
    
    def mat_sub(a, b):
        return [
            [a[0][0] - b[0][0], a[0][1] - b[0][1]],
            [a[1][0] - b[1][0], a[1][1] - b[1][1]]
        ]
    
    mu_nu = mat_mul(h_mu, h_nu)
    nu_mu = mat_mul(h_nu, h_mu)
    return mat_sub(mu_nu, nu_mu)


def _expm(m: list, steps: int = 10) -> list:
    """Compute matrix exponential via series expansion."""
    import cmath
    
    result = [[1, 0], [0, 1]]
    term = [[1, 0], [0, 1]]
    
    for k in range(1, steps + 1):
        # Multiply term by m/k
        new_term = [[term[0][0] * m[j][i] / k for j in range(2)] for i in range(2)]
        for i in range(2):
            for j in range(2):
                term[i][j] = sum(term[i][k] * m[k][j] for k in range(2)) / k
        # Add to result
        for i in range(2):
            for j in range(2):
                result[i][j] += term[i][j]
    
    return result


def get_discrete_curvature(h_sequence: list) -> float:
    """Compute the holonomic curvature (angle) for a sequence of su(2) matrices.
    
    Uses the trace of the ordered product (parallel transport).
    Returns value in [0, π].
    """
    if not h_sequence:
        return 0.0
    
    # Parallel transport: ordered exponential
    transport = [[1, 0], [0, 1]]
    for h in h_sequence:
        transport = _ordered_multiply(transport, _expm(h))
    
    # Holonomy angle from trace
    trace_val = transport[0][0] + transport[1][1]
    w = abs(trace_val.real) / 2
    w = max(0.0, min(1.0, w))
    return 2.0 * _safe_acos(w)


def _safe_acos(x: float) -> float:
    """Safe arccos that handles floating point errors."""
    import cmath
    if x >= 1.0:
        return 0.0
    if x <= -1.0:
        return 3.141592653589793
    return _acos(x)


def _acos(x: float) -> float:
    """Real arccos using series expansion."""
    import cmath
    if -1 <= x <= 1:
        return (1.5707963267948966 - _asin(x))
    return cmath.acos(x).real


def _asin(x: float) -> float:
    """Real arcsin using series expansion."""
    if abs(x) >= 1:
        return 1.5707963267948966 if x >= 0 else -1.5707963267948966
    result = x
    term = x
    x2 = x * x
    for n in range(1, 100):
        term *= x2 * (2 * n - 1) * (2 * n - 1) / ((2 * n) * (2 * n + 1))
        result += term
        if abs(term) < 1e-15:
            break
    return result


def _ordered_multiply(a: list, b: list) -> list:
    """Matrix multiplication."""
    return [
        [a[0][0]*b[0][0] + a[0][1]*b[1][0], a[0][0]*b[0][1] + a[0][1]*b[1][1]],
        [a[1][0]*b[0][0] + a[1][1]*b[1][0], a[1][0]*b[0][1] + a[1][1]*b[1][1]]
    ]


def get_field_tension(h_matrix: list) -> float:
    """Compute the field tension/energy: Tr(H†H).
    
    For SU(2), tension is the sum of squared components.
    """
    # Tr(H†H) = sum of |H_ij|^2 for Hermitian H
    tension = 0.0
    for row in h_matrix:
        for val in row:
            tension += abs(val) ** 2
    return tension


def get_lyapunov_deviation(h_state: list, h_baseline: list) -> float:
    """Compute the deviation (tension) between a local state and a baseline.
    
    Uses PRISM correlation for quantum fidelity measurement.
    """
    state_coord = get_field_state(h_state).prism_coordinate
    baseline_coord = get_field_state(h_baseline).prism_coordinate
    
    # PRISM correlation gives fidelity
    correlation = GAUGE_ENGINE.correlate(state_coord, baseline_coord)
    
    # Deviation = 1 - fidelity
    return 1.0 - correlation['fidelity']


def get_prism_correlation(state_a: list, state_b: list) -> dict:
    """Compute PRISM correlation between two field states."""
    coord_a = get_field_state(state_a).prism_coordinate
    coord_b = get_field_state(state_b).prism_coordinate
    return GAUGE_ENGINE.correlate(coord_a, coord_b)


def analyze_resonance(
    h_sequence: list,
    locations: list,
    include_prism: bool = True
) -> ResonanceAnalysis:
    """Analyze the holonomic consistency of a field sequence.
    
    Now with optional PRISM correlation analysis.
    """
    global_kappa = get_discrete_curvature(h_sequence)

    # Local curvatures (sliding window)
    local_curvatures = []
    for i in range(len(h_sequence) - 4):
        window = h_sequence[i:i+5]
        kappa = get_discrete_curvature(window)
        local_curvatures.append({
            'start': locations[i] if i < len(locations) else f"pos_{i}",
            'end': locations[i+4] if i+4 < len(locations) else f"pos_{i+4}",
            'curvature': float(kappa),
        })

    hotspots = sorted(local_curvatures, key=lambda x: x['curvature'], reverse=True)[:10]

    if global_kappa < 0.5:
        consistency = "highly_consistent"
    elif global_kappa < 1.5:
        consistency = "moderately_consistent"
    else:
        consistency = "context_dependent"

    # PRISM integration
    prism_correlation = None
    derivation_id = None
    
    if include_prism and len(h_sequence) >= 2:
        first_coord = get_field_state(h_sequence[0]).prism_coordinate
        last_coord = get_field_state(h_sequence[-1]).prism_coordinate
        prism_correlation = GAUGE_ENGINE.correlate(first_coord, last_coord)
        
        # Convert tuples to ints for derivation
        first_int = GAUGE_ENGINE._from_bytes(first_coord)
        last_int = GAUGE_ENGINE._from_bytes(last_coord)
        
        # Generate derivation for the curvature computation
        curvature_term = GAUGE_ENGINE.make_term("xor", first_int, last_int)
        derivation = GAUGE_ENGINE.derive(curvature_term)
        derivation_id = derivation.derivation_id

    return ResonanceAnalysis(
        global_curvature=float(global_kappa),
        consistency=consistency,
        hotspots=hotspots,
        prism_correlation=prism_correlation,
        derivation_id=derivation_id
    )


def derive_curvature_state(h_sequence: list) -> dict:
    """Create derivation for a holonomic curvature computation.
    
    Returns derivation certificate with provenance.
    """
    if not h_sequence:
        return {'derivation': None, 'curvature': 0.0}
    
    # Create PRISM derivation for the field state sequence
    coords = [get_field_state(h).prism_coordinate for h in h_sequence]
    
    # Convert to integers for derivation
    ints = [GAUGE_ENGINE._from_bytes(c) for c in coords]
    
    # XOR all coordinates to get combined state
    if len(ints) == 1:
        combined = coords[0]
    else:
        combined = GAUGE_ENGINE.xor(coords[0], coords[1])
        for c in coords[2:]:
            combined = GAUGE_ENGINE.xor(combined, c)
    
    # Create term from integers
    term = GAUGE_ENGINE.make_term("xor", ints[0], ints[1]) if len(ints) > 1 else None
    
    curvature = get_discrete_curvature(h_sequence)
    
    return {
        'curvature': curvature,
        'prism_coordinate': combined,
        'prism_triplet': GAUGE_ENGINE.triad(combined),
        'derivation': GAUGE_ENGINE.derive(term) if term else None
    }
