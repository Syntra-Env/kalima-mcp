"""
UOR Ring Substrate Standards
==============================

Axioms defining the Z/(2^256)Z ring and dihedral symmetry implementation.
These are the formal rules that the geometer.uor module MUST satisfy.
"""

# Ring Parameters
RING_QUANTUM: int = 256          # n = 256 bits
MODULUS: int = 2 ** RING_QUANTUM  # 2^256
MASK: int = MODULUS - 1           # 0xFFFF...FF

# Required Generators (from D_2n dihedral group)
REQUIRED_GENERATORS: list[str] = [
    "neg",     # Arithmetic negation: -x mod 2^n
    "bnot",    # Bitwise NOT: ~x mod 2^n
    "succ",    # Successor: x + 1 mod 2^n
]

# Core Identities (MUST hold for ALL x in the ring)
CORE_IDENTITIES: list[tuple[str, str]] = [
    ("neg(bnot(x))", "succ(x)"),           # Fundamental dihedral relation
    ("neg(neg(x))", "x"),                  # Involution of negation
    ("bnot(bnot(x))", "x"),                # Involution of bitwise NOT
    ("succ(succ(neg(x)))", "x"),           # Combined relation
]

# Metric Bounds
METRIC_BOUNDS: dict[str, tuple[float, float]] = {
    "hamming_distance": (0.0, 256.0),      # d_H ∈ [0, 256]
    "ring_distance": (0.0, 2**255),         # d_R ∈ [0, 2^255]
    "incompatibility": (0.0, 1.0),          # d_Δ ∈ [0, 1]
}

# Dihedral Orbit Structure
DIHEDRAL_ORBIT_SIZE: int = 4
DIHEDRAL_ELEMENTS: list[str] = [
    "identity",      # x
    "neg",           # -x mod 2^n
    "bnot",          # ~x mod 2^n
    "neg_bnot",      # -(~x) mod 2^n
]

# Fiber Decomposition
FIBER_COUNT: int = 256              # 256 binary fibers (Z/2Z)
STRATUM_MAX: int = 2048              # Maximum stratum (32 bytes × 8 bits/byte)

# Example Valid Ring Elements for Testing
TEST_ELEMENTS: list[int] = [
    0,              # Zero
    1,              # Identity
    MASK,           # Max element (-1 mod 2^256)
    MASK >> 1,      # Half max
    0xDEADBEEF,     # Known pattern
]
