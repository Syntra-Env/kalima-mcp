"""Geometer Conformance Standards.

This package defines the formal axioms and rules that Geometer
MUST satisfy to be considered conforming to its own specification.

Each module in standards/ contains the axioms for a corresponding
implementation module in src/geometer/.
"""

from .uor_ring import *
from .root_space import *
from .gauge import *

__all__ = [
    # Ring
    "RING_QUANTUM",
    "MODULUS",
    "MASK",
    "REQUIRED_GENERATORS",
    "CORE_IDENTITIES",
    "METRIC_BOUNDS",
    "DIHEDRAL_ORBIT_SIZE",
    "FIBER_COUNT",
    "TEST_ELEMENTS",
    # Root Space
    "TOTAL_PROFILE_DIM",
    "METRIC_BOUNDS",
    "MAX_SURAHS",
    "REQUIRED_ROOT_FIELDS",
    # Gauge
    "LIE_ALGEBRA_DIMENSION",
    "MATRIX_DIMENSION",
    "METRIC_BOUNDS",
    "CONSISTENCY_LEVELS",
]
