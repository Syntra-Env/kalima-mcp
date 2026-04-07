"""
Root Space Standards
====================

Axioms defining the distributional vector representation of Arabic roots.
These are the formal rules that the geometer.root_space module MUST satisfy.
"""

# Profile Dimension Counts (MUST match enumerated keys)
POS_DIM: int = 45
VF_DIM: int = 12       # Verb form dimensions (I-XII)
ASP_DIM: int = 3        # Aspect: PERF, IMPF, IMPV
PER_DIM: int = 3        # Person: 1, 2, 3
NUM_DIM: int = 3        # Number: S, D, P
GEN_DIM: int = 2        # Gender: M, F
CAS_DIM: int = 3        # Case: NOM, ACC, GEN

TOTAL_PROFILE_DIM: int = POS_DIM + VF_DIM + ASP_DIM + PER_DIM + NUM_DIM + GEN_DIM + CAS_DIM
# Expected: 46 + 12 + 3 + 3 + 3 + 2 + 3 = 72

# Bounds (all metrics MUST be within these ranges)
METRIC_BOUNDS: dict[str, tuple[float, float]] = {
    "distributional_weight": (0.0, 1.0),   # w ∈ [0, 1]
    "anomaly_score": (0.0, 1.0),           # a ∈ [0, 1]
    "concordance_distance": (0.0, 1.0),    # d ∈ [0, 1]
    "profile_value": (0.0, 1.0),           # Each profile element is normalized
}

# Profile Normalization Requirement
# After normalization: sum(profile) == 1.0 (or == 0 if all zeros)

# Surah Coverage (Quran has 114 surahs)
MAX_SURAHS: int = 114

# Morphological Diversity Threshold
# Used in distributional_weight calculation
MORPHEME_TYPES_REFERENCE: int = 20

# Profile Vector Constraints
PROFILE_CONSTRAINTS: dict[str, object] = {
    "non_negative": True,           # All values >= 0
    "normalized": True,              # Sum == 1.0 after normalization
    "dimensionality": TOTAL_PROFILE_DIM,
}

# RootVector Required Fields
REQUIRED_ROOT_FIELDS: list[str] = [
    "root_id",
    "lookup_key",
    "label_ar",
    "total_instances",
    "total_verses",
    "total_surahs",
    "total_morpheme_types",
    "total_lemmas",
    "profile",
    "cooccurrence_counts",
    "surah_set",
    "verse_locations",
]

# Derived Property Requirements
DERIVED_PROPERTY_BOUNDS: dict[str, tuple[float, float]] = {
    "distributional_weight": (0.0, 1.0),
}

# Distance Metric Requirements
DISTANCE_METRIC_PROPERTIES: dict[str, bool] = {
    "non_negative": True,      # d(x,y) >= 0
    "symmetric": True,         # d(x,y) == d(y,x)
    "identity_of_indiscernibles": True,  # d(x,x) == 0
    "triangle_inequality": True,  # d(x,z) <= d(x,y) + d(y,z)
}
