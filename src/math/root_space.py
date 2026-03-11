"""Root Space: Distributional vector representation of Arabic roots.

A root is NOT a scalar. It is characterized by its full usage pattern
across the entire Quran:

  - Which POS forms it takes (verb, noun, adjective, etc.)
  - Which morphological patterns (awzan) it participates in
  - Which grammatical features it manifests (person, number, gender, case)
  - How many verses it appears in and how spread out they are
  - What other roots co-occur with it in the same verses

This gives each root a high-dimensional fingerprint. Two roots are
"close" if they behave similarly across the Quran — not if their
hashes are similar, and not if they're both rare.

Key concepts:
  - distributional_weight: how central a root is (frequent, spread across
    many surahs = structural pillar). Opposite of surprisal.
  - anomaly_score: how unusual a SPECIFIC INSTANCE is relative to the
    root's typical behavior. This is what surprisal was trying to be.
  - concordance_distance: similarity between two roots based on their
    distributional overlap.
"""

import numpy as np
from dataclasses import dataclass, field


# ── Feature vocabulary (fixed order for vector dimensions) ──

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

# Index maps for fast lookup
_POS_IDX = {k: i for i, k in enumerate(POS_KEYS)}
_VF_IDX = {k: i for i, k in enumerate(VERB_FORM_KEYS)}
_ASP_IDX = {k: i for i, k in enumerate(ASPECT_KEYS)}
_PER_IDX = {k: i for i, k in enumerate(PERSON_KEYS)}
_NUM_IDX = {k: i for i, k in enumerate(NUMBER_KEYS)}
_GEN_IDX = {k: i for i, k in enumerate(GENDER_KEYS)}
_CAS_IDX = {k: i for i, k in enumerate(CASE_KEYS)}

# Total vector dimensions
POS_DIM = len(POS_KEYS)
VF_DIM = len(VERB_FORM_KEYS)
ASP_DIM = len(ASPECT_KEYS)
PER_DIM = len(PERSON_KEYS)
NUM_DIM = len(NUMBER_KEYS)
GEN_DIM = len(GENDER_KEYS)
CAS_DIM = len(CASE_KEYS)

PROFILE_DIM = POS_DIM + VF_DIM + ASP_DIM + PER_DIM + NUM_DIM + GEN_DIM + CAS_DIM


from .gauge import analyze_resonance, ResonanceAnalysis


@dataclass
class RootVector:
    """Distributional vector for a single Arabic root.

    Built from ALL instances of this root across the Quran.
    """
    root_id: int
    lookup_key: str           # e.g. "سجد"
    label_ar: str | None

    # Raw counts
    total_instances: int = 0  # total word occurrences
    total_verses: int = 0     # distinct verses
    total_surahs: int = 0     # distinct surahs
    total_morpheme_types: int = 0  # distinct morpheme forms
    total_lemmas: int = 0     # distinct lemmas

    # Distributional profile: normalized frequency of each feature value
    # across all morpheme types of this root.
    # Shape: (PROFILE_DIM,) — concatenation of POS + VF + ASP + PER + NUM + GEN + CAS
    profile: np.ndarray = field(default_factory=lambda: np.zeros(PROFILE_DIM))

    # Co-occurrence fingerprint: {other_root_id: count_of_shared_verses}
    cooccurrence_counts: dict[int, int] = field(default_factory=dict)

    # Surah spread: which surahs this root appears in (set of ints)
    surah_set: set[int] = field(default_factory=set)

    # Verse locations: list of (surah, ayah) tuples
    verse_locations: list[tuple[int, int]] = field(default_factory=list)

    @property
    def distributional_weight(self) -> float:
        """How central is this root in the Quran?

        High = structural pillar (appears in many surahs, many forms).
        Low = peripheral or specialized.

        Uses surah spread * morphological diversity, not raw frequency.
        A root in 50 surahs with 10 forms is more central than one
        in 2 surahs with 100 instances of the same form.
        """
        if self.total_instances == 0:
            return 0.0
        surah_spread = self.total_surahs / 114.0
        form_diversity = min(self.total_morpheme_types / 20.0, 1.0)
        return surah_spread * 0.6 + form_diversity * 0.4

    @property
    def pos_distribution(self) -> np.ndarray:
        """POS slice of the profile vector."""
        return self.profile[:POS_DIM]

    @property
    def verb_form_distribution(self) -> np.ndarray:
        """Verb form slice."""
        start = POS_DIM
        return self.profile[start:start + VF_DIM]

    @property
    def aspect_distribution(self) -> np.ndarray:
        """Aspect slice."""
        start = POS_DIM + VF_DIM
        return self.profile[start:start + ASP_DIM]


def build_root_vector(
    root_id: int,
    lookup_key: str,
    label_ar: str | None,
    morpheme_features: list[dict],
    instance_locations: list[tuple[int, int]],
    cooccurrence_counts: dict[int, int] | None = None,
) -> RootVector:
    """Build a RootVector from raw morpheme data.

    Args:
        root_id: feature ID of the root
        lookup_key: e.g. "سجد"
        label_ar: Arabic label
        morpheme_features: list of dicts, one per morpheme type, with keys:
            pos, verb_form, aspect, person, number, gender, case_value, lemma
        instance_locations: list of (surah, ayah) for every word instance
        cooccurrence_counts: dict of {other_root_id: count}
    """
    rv = RootVector(
        root_id=root_id,
        lookup_key=lookup_key,
        label_ar=label_ar,
        cooccurrence_counts=cooccurrence_counts or {},
    )

    # Count instances and spread
    rv.verse_locations = instance_locations
    verse_set = set(instance_locations)
    rv.total_instances = len(instance_locations)
    rv.total_verses = len(verse_set)
    rv.surah_set = {s for s, a in verse_set}
    rv.total_surahs = len(rv.surah_set)
    rv.total_morpheme_types = len(morpheme_features)

    lemmas = set()
    profile = np.zeros(PROFILE_DIM)

    for mf in morpheme_features:
        # POS
        pos = mf.get("pos")
        if pos and pos in _POS_IDX:
            profile[_POS_IDX[pos]] += 1

        # Verb form
        vf = mf.get("verb_form")
        if vf and vf in _VF_IDX:
            profile[POS_DIM + _VF_IDX[vf]] += 1

        # Aspect
        asp = mf.get("aspect")
        if asp and asp in _ASP_IDX:
            profile[POS_DIM + VF_DIM + _ASP_IDX[asp]] += 1

        # Person
        per = mf.get("person")
        if per and per in _PER_IDX:
            offset = POS_DIM + VF_DIM + ASP_DIM
            profile[offset + _PER_IDX[per]] += 1

        # Number
        num = mf.get("number")
        if num and num in _NUM_IDX:
            offset = POS_DIM + VF_DIM + ASP_DIM + PER_DIM
            profile[offset + _NUM_IDX[num]] += 1

        # Gender
        gen = mf.get("gender")
        if gen and gen in _GEN_IDX:
            offset = POS_DIM + VF_DIM + ASP_DIM + PER_DIM + NUM_DIM
            profile[offset + _GEN_IDX[gen]] += 1

        # Case
        cas = mf.get("case_value")
        if cas and cas in _CAS_IDX:
            offset = POS_DIM + VF_DIM + ASP_DIM + PER_DIM + NUM_DIM + GEN_DIM
            profile[offset + _CAS_IDX[cas]] += 1

        # Lemma tracking
        lemma = mf.get("lemma")
        if lemma:
            lemmas.add(lemma)

    rv.total_lemmas = len(lemmas)

    # Normalize profile to probability distribution
    total = profile.sum()
    if total > 0:
        rv.profile = profile / total
    else:
        rv.profile = profile

    return rv


def instance_anomaly(root_vector: RootVector, instance_features: dict) -> float:
    """How unusual is a specific instance relative to its root's typical behavior?

    Returns a score in [0, 1]:
      0 = this instance uses the most common form of this root (typical)
      1 = this instance uses a form never seen for this root (maximally anomalous)

    Computes anomaly per feature subspace (POS, verb_form, aspect, etc.)
    independently, then averages across subspaces that have data.
    This avoids the dilution problem of one big normalized vector.

    A hapax legomenon root will have anomaly=0 for its only form
    (it IS the distribution), but distributional_weight will be near 0.
    """
    if root_vector.total_morpheme_types <= 1:
        return 0.0

    # Define subspaces: (start_idx, dim, index_map, feature_key)
    subspaces = [
        (0, POS_DIM, _POS_IDX, "pos"),
        (POS_DIM, VF_DIM, _VF_IDX, "verb_form"),
        (POS_DIM + VF_DIM, ASP_DIM, _ASP_IDX, "aspect"),
        (POS_DIM + VF_DIM + ASP_DIM, PER_DIM, _PER_IDX, "person"),
        (POS_DIM + VF_DIM + ASP_DIM + PER_DIM, NUM_DIM, _NUM_IDX, "number"),
        (POS_DIM + VF_DIM + ASP_DIM + PER_DIM + NUM_DIM, GEN_DIM, _GEN_IDX, "gender"),
        (POS_DIM + VF_DIM + ASP_DIM + PER_DIM + NUM_DIM + GEN_DIM, CAS_DIM, _CAS_IDX, "case_value"),
    ]

    anomaly_scores = []
    for start, dim, idx_map, feat_key in subspaces:
        val = instance_features.get(feat_key)
        if not val or val not in idx_map:
            continue  # this subspace not active for this instance

        # Get the sub-distribution for this feature space
        sub_profile = root_vector.profile[start:start + dim]
        sub_total = sub_profile.sum()
        if sub_total == 0:
            anomaly_scores.append(1.0)  # root never uses this subspace
            continue

        # Probability of this specific value within the subspace
        prob = sub_profile[idx_map[val]] / sub_total
        anomaly_scores.append(1.0 - prob)

    if not anomaly_scores:
        return 0.0

    return float(np.mean(anomaly_scores))


def concordance_distance(rv_a: RootVector, rv_b: RootVector) -> float:
    """Distance between two roots based on distributional overlap.

    Uses Jensen-Shannon divergence on their profile vectors.
    Returns value in [0, 1]: 0 = identical distributions, 1 = disjoint.
    """
    p = rv_a.profile
    q = rv_b.profile

    # Handle zero vectors
    if p.sum() == 0 or q.sum() == 0:
        return 1.0

    # Jensen-Shannon divergence
    m = 0.5 * (p + q)

    # KL divergence with epsilon to avoid log(0)
    eps = 1e-12
    kl_pm = np.sum(p * np.log((p + eps) / (m + eps)))
    kl_qm = np.sum(q * np.log((q + eps) / (m + eps)))

    jsd = 0.5 * (kl_pm + kl_qm)
    return float(np.clip(np.sqrt(jsd), 0.0, 1.0))  # sqrt for metric property
