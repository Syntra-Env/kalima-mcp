"""
Root Space: PRISM-Native Distributional Analysis of Arabic Roots.

This module extends PRISM to represent Arabic roots as triadic coordinates
and computes similarity using PRISM's correlation engine.

A root is characterized by its full usage pattern across the Quran:
  - Which POS forms it takes (verb, noun, adjective, etc.)
  - Which morphological patterns (awzan) it participates in
  - Which grammatical features it manifests
  - How many verses it appears in and how spread out they are

Each root's distributional profile is encoded as a PRISM coordinate.
Two roots are "close" if their PRISM coordinates correlate.

Key concepts (now PRISM-native):
  - prism_coordinate: PRISM triadic address for this root's profile
  - distributional_weight: derived from stratum (total information content)
  - anomaly_score: PRISM fidelity deviation from root's typical behavior
  - concordance_distance: PRISM correlation between root coordinates
"""

from dataclasses import dataclass, field
from typing import Optional

from .prism import UOR, Triad
from .uor import Q256


# ── Feature vocabulary (fixed order for profile encoding) ──

POS_KEYS = [
    "N", "V", "ADJ", "DET", "CONJ", "P", "PRON", "PN",
    "REM", "EMPH", "INTG", "T", "LOC", "REL", "ACC",
    "COND", "DEM", "NEG", "VOC", "SUB", "FUT", "PRP",
    "CIRC", "SUP", "RSLT", "INL", "CERT", "CAUS", "INT",
    "AMD", "EXL", "SUR", "ANS", "EQ", "EXH", "INC",
    "PREV", "IMPV", "AVR", "EXP", "PRO", "RES", "RET",
    "IMPN", "COM",
]

VERB_FORM_KEYS = [
    "(I)", "(II)", "(III)", "(IV)", "(V)", "(VI)", "(VII)",
    "(VIII)", "(IX)", "(X)", "(XI)", "(XII)",
]

ASPECT_KEYS = ["PERF", "IMPF", "IMPV"]

PERSON_KEYS = ["1", "2", "3"]
NUMBER_KEYS = ["S", "D", "P"]
GENDER_KEYS = ["M", "F"]
CASE_KEYS = ["NOM", "ACC", "GEN"]

# Index maps
_POS_IDX = {k: i for i, k in enumerate(POS_KEYS)}
_VF_IDX = {k: i for i, k in enumerate(VERB_FORM_KEYS)}
_ASP_IDX = {k: i for i, k in enumerate(ASPECT_KEYS)}
_PER_IDX = {k: i for i, k in enumerate(PERSON_KEYS)}
_NUM_IDX = {k: i for i, k in enumerate(NUMBER_KEYS)}
_GEN_IDX = {k: i for i, k in enumerate(GENDER_KEYS)}
_CAS_IDX = {k: i for i, k in enumerate(CASE_KEYS)}

# Dimensions
POS_DIM = len(POS_KEYS)
VF_DIM = len(VERB_FORM_KEYS)
ASP_DIM = len(ASPECT_KEYS)
PER_DIM = len(PERSON_KEYS)
NUM_DIM = len(NUMBER_KEYS)
GEN_DIM = len(GENDER_KEYS)
CAS_DIM = len(CASE_KEYS)

PROFILE_DIM = POS_DIM + VF_DIM + ASP_DIM + PER_DIM + NUM_DIM + GEN_DIM + CAS_DIM

# Quran bounds
MAX_SURAHS = 114
MAX_VERSES = 6236


@dataclass
class RootVector:
    """Distributional vector for a single Arabic root.
    
    Built from ALL instances of this root across the Quran.
    Now with PRISM-native coordinate representation.
    """
    root_id: int
    lookup_key: str           # e.g. "سجد"
    label_ar: Optional[str]

    # Raw counts
    total_instances: int = 0
    total_verses: int = 0
    total_surahs: int = 0
    total_morpheme_types: int = 0
    total_lemmas: int = 0

    # Profile as list (encoded to PRISM coordinate)
    profile: list[float] = field(default_factory=lambda: [0.0] * PROFILE_DIM)

    # Co-occurrence fingerprint
    cooccurrence_counts: dict[int, int] = field(default_factory=dict)

    # Surah spread
    surah_set: set = field(default_factory=set)

    # Verse locations
    verse_locations: list = field(default_factory=list)

    # ── PRISM Integration ──────────────────────────────────────────

    @property
    def prism_triplet(self) -> Triad:
        """PRISM triadic coordinate derived from profile.
        
        Encodes the distributional profile as a byte sequence,
        then maps to PRISM coordinates (datum, stratum, spectrum).
        """
        triplet = _profile_to_prism_triplet(self.profile)
        return triplet

    @property
    def prism_coordinate(self) -> tuple:
        """PRISM datum (byte tuple) for this root's profile."""
        return Q256._to_bytes(_profile_to_int(self.profile))

    @property
    def prism_derivation_id(self) -> str:
        """Content-addressed derivation ID for this root's profile."""
        coord = self.prism_coordinate
        return Q256._iri(coord)

    @property
    def distributional_weight(self) -> float:
        """How central is this root in the Quran?
        
        Derived from PRISM stratum: higher stratum = more information = more central.
        """
        if self.total_instances == 0:
            return 0.0
        # Stratum-based: higher popcount = more diverse = more central
        triad = self.prism_triplet
        stratum_normalized = triad.total_stratum / (PROFILE_DIM * 8)
        surah_spread = self.total_surahs / MAX_SURAHS
        form_diversity = min(self.total_morpheme_types / 20.0, 1.0)
        return (stratum_normalized * 0.3 + surah_spread * 0.5 + form_diversity * 0.2)

    @property
    def information_content(self) -> float:
        """PRISM stratum as information content (bits)."""
        return float(self.prism_triplet.total_stratum)

    @property
    def profile_bytes(self) -> bytes:
        """Profile encoded as bytes for PRISM coordinate."""
        return _profile_to_bytes(self.profile)


@dataclass  
class InstanceVector:
    """A single usage instance of a root, with PRISM coordinates."""
    root: RootVector
    location: tuple  # (surah, ayah)
    features: dict

    @property
    def prism_coordinate(self) -> tuple:
        """Instance-specific PRISM coordinate."""
        return Q256._to_bytes(_features_to_int(self.features))

    @property
    def anomaly_score(self) -> float:
        """PRISM fidelity deviation from root's typical behavior.
        
        Uses PRISM correlation between instance and root coordinates.
        """
        root_coord = self.root.prism_coordinate
        instance_coord = self.prism_coordinate
        correlation = Q256.correlate_ints(root_coord, instance_coord)
        return 1.0 - correlation['fidelity']


def _profile_to_bytes(profile: list[float]) -> bytes:
    """Encode normalized profile [0,1] as bytes for PRISM."""
    # Scale to 0-255 per dimension, take first 32 bytes
    encoded = bytearray(min(32, len(profile)))
    for i in range(len(encoded)):
        val = int(profile[i] * 255) if i < len(profile) else 0
        encoded[i] = min(255, max(0, val))
    return bytes(encoded)


def _profile_to_int(profile: list[float]) -> int:
    """Encode profile as integer for PRISM coordinate."""
    encoded = _profile_to_bytes(profile)
    return int.from_bytes(encoded, 'big')


def _profile_to_prism_triplet(profile: list[float]) -> Triad:
    """Convert profile to PRISM triadic coordinate."""
    triplet = Q256._to_bytes(_profile_to_int(profile))
    return Q256.triad(triplet)


def _features_to_int(features: dict) -> int:
    """Encode instance features as integer for PRISM coordinate."""
    encoded = bytearray(32)
    
    if 'pos' in features and features['pos'] in _POS_IDX:
        encoded[0] = _POS_IDX[features['pos']]
    if 'verb_form' in features and features['verb_form'] in _VF_IDX:
        encoded[1] = _VF_IDX[features['verb_form']]
    if 'aspect' in features and features['aspect'] in _ASP_IDX:
        encoded[2] = _ASP_IDX[features['aspect']]
    if 'person' in features and features['person'] in _PER_IDX:
        encoded[3] = _PER_IDX[features['person']]
    if 'number' in features and features['number'] in _NUM_IDX:
        encoded[4] = _NUM_IDX[features['number']]
    if 'gender' in features and features['gender'] in _GEN_IDX:
        encoded[5] = _GEN_IDX[features['gender']]
    if 'case_value' in features and features['case_value'] in _CAS_IDX:
        encoded[6] = _CAS_IDX[features['case_value']]
    
    return int.from_bytes(bytes(encoded), 'big')


def build_root_vector(
    root_id: int,
    lookup_key: str,
    label_ar: Optional[str],
    morpheme_features: list[dict],
    instance_locations: list[tuple],
    cooccurrence_counts: dict[int, int] | None = None,
) -> RootVector:
    """Build a RootVector from raw morpheme data."""
    rv = RootVector(
        root_id=root_id,
        lookup_key=lookup_key,
        label_ar=label_ar,
        cooccurrence_counts=cooccurrence_counts or {},
    )

    rv.verse_locations = instance_locations
    verse_set = set(instance_locations)
    rv.total_instances = len(instance_locations)
    rv.total_verses = len(verse_set)
    rv.surah_set = {s for s, a in verse_set}
    rv.total_surahs = len(rv.surah_set)
    rv.total_morpheme_types = len(morpheme_features)

    lemmas = set()
    profile = [0.0] * PROFILE_DIM

    for mf in morpheme_features:
        pos = mf.get("pos")
        if pos and pos in _POS_IDX:
            profile[_POS_IDX[pos]] += 1

        vf = mf.get("verb_form")
        if vf and vf in _VF_IDX:
            profile[POS_DIM + _VF_IDX[vf]] += 1

        asp = mf.get("aspect")
        if asp and asp in _ASP_IDX:
            profile[POS_DIM + VF_DIM + _ASP_IDX[asp]] += 1

        per = mf.get("person")
        if per and per in _PER_IDX:
            offset = POS_DIM + VF_DIM + ASP_DIM
            profile[offset + _PER_IDX[per]] += 1

        num = mf.get("number")
        if num and num in _NUM_IDX:
            offset = POS_DIM + VF_DIM + ASP_DIM + PER_DIM
            profile[offset + _NUM_IDX[num]] += 1

        gen = mf.get("gender")
        if gen and gen in _GEN_IDX:
            offset = POS_DIM + VF_DIM + ASP_DIM + PER_DIM + NUM_DIM
            profile[offset + _GEN_IDX[gen]] += 1

        cas = mf.get("case_value")
        if cas and cas in _CAS_IDX:
            offset = POS_DIM + VF_DIM + ASP_DIM + PER_DIM + NUM_DIM + GEN_DIM
            profile[offset + _CAS_IDX[cas]] += 1

        lemma = mf.get("lemma")
        if lemma:
            lemmas.add(lemma)

    rv.total_lemmas = len(lemmas)

    # Normalize
    total = sum(profile)
    if total > 0:
        rv.profile = [p / total for p in profile]
    else:
        rv.profile = profile

    return rv


def instance_anomaly(root_vector: RootVector, instance_features: dict) -> float:
    """PRISM-native anomaly: fidelity deviation from root's typical behavior."""
    instance_coord = _features_to_int(instance_features)
    root_coord = _profile_to_int(root_vector.profile)
    
    correlation = Q256.correlate(root_coord, instance_coord)
    return 1.0 - correlation['fidelity']


def concordance_distance(rv_a: RootVector, rv_b: RootVector) -> float:
    """PRISM correlation-based distance between roots.
    
    Uses PRISM fidelity: 1 = identical, 0 = maximally different.
    Returns distance: 0 = identical, 1 = maximally different.
    """
    coord_a = _profile_to_int(rv_a.profile)
    coord_b = _profile_to_int(rv_b.profile)
    
    correlation = Q256.correlate(coord_a, coord_b)
    return 1.0 - correlation['fidelity']


def root_correlation(rv_a: RootVector, rv_b: RootVector) -> dict:
    """Full PRISM correlation between two roots."""
    coord_a = _profile_to_int(rv_a.profile)
    coord_b = _profile_to_int(rv_b.profile)
    
    return Q256.correlate(coord_a, coord_b)


def derive_concordance(rv_a: RootVector, rv_b: RootVector) -> dict:
    """Create derivation certificate for concordance computation.
    
    Returns derivation with provenance for the distance computation.
    """
    term = Q256.make_term("xor", rv_a.prism_coordinate, rv_b.prism_coordinate)
    derivation = Q256.derive(term)
    
    return {
        'derivation': derivation,
        'distance': concordance_distance(rv_a, rv_b),
        'correlation': Q256.correlate(
            _profile_to_int(rv_a.profile),
            _profile_to_int(rv_b.profile)
        )
    }
