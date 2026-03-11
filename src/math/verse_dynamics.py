"""Verse Dynamics: Sequence analysis over distributional root vectors.

Replaces the old su(2) → Pauli → holonomy pipeline with direct
computation on root distributional vectors. No arbitrary gauge group
choice — the math operates on the actual morphological structure.

Four signals per word, grounded in Arabic linguistics:

  weight    = distributional_weight of the root.
              High = structural pillar (ربب=0.87). Low = peripheral (هيت=0.03).
              This is the root's importance in the Quran as a whole.

  anomaly   = instance_anomaly of this specific usage.
              High = unusual form for this root. Low = typical form.
              This flags when a root is used in an unexpected way.

  drift     = how much the morphological profile changes between adjacent words.
              High = the verse shifts semantic/grammatical gears at this point.
              Replaces old E_d = ‖H_curr - H_prev‖².

  coherence = how similar adjacent words' root profiles are.
              High = continuation (same topic/speaker). Low = boundary.
              Replaces old phase-lock Φ.
"""

import numpy as np
from dataclasses import dataclass
from .root_space import (
    RootVector, instance_anomaly, PROFILE_DIM,
    _POS_IDX, _VF_IDX, _ASP_IDX, _PER_IDX, _NUM_IDX, _GEN_IDX, _CAS_IDX,
    POS_DIM, VF_DIM, ASP_DIM, PER_DIM, NUM_DIM, GEN_DIM, CAS_DIM,
)


@dataclass
class WordAnalysis:
    """Analysis of a single word in a verse."""
    word_index: int
    text: str
    root_key: str | None       # e.g. "سجد", None if no root (particles)
    weight: float              # distributional_weight of the root
    anomaly: float             # instance_anomaly for this usage
    drift: float               # profile distance from previous word
    coherence: float           # profile similarity with next word

    @property
    def energy(self) -> float:
        """Total energy of this word = weight + anomaly + drift.

        High energy = this word demands interpretive attention.
        Weight contributes because structurally central roots carry meaning.
        Anomaly contributes because unusual usage is a signal.
        Drift contributes because positional shifts are significant.
        """
        return self.weight + self.anomaly + self.drift


@dataclass
class VerseAnalysis:
    """Full analysis of a verse's dynamics."""
    surah: int
    ayah: int
    words: list[WordAnalysis]

    @property
    def emphasis(self) -> dict[str, float]:
        """Emphasis profile: which dimension dominates this verse?

        Returns normalized weights for:
          root:     how much structural root weight drives this verse
          anomaly:  how much unusual usage drives this verse
          position: how much word-order dynamics drive this verse
          boundary: how much coherence drop signals a break
        """
        if not self.words:
            return {"root": 0.25, "anomaly": 0.25, "position": 0.25, "boundary": 0.25}

        total_weight = sum(w.weight for w in self.words)
        total_anomaly = sum(w.anomaly for w in self.words)
        total_drift = sum(w.drift for w in self.words)

        # Boundary signal: average incoherence (1 - coherence)
        coherences = [w.coherence for w in self.words if w.coherence is not None]
        avg_incoherence = 1.0 - (sum(coherences) / len(coherences)) if coherences else 0.0

        total = total_weight + total_anomaly + total_drift + avg_incoherence
        if total < 1e-12:
            return {"root": 0.25, "anomaly": 0.25, "position": 0.25, "boundary": 0.25}

        return {
            "root": round(total_weight / total, 3),
            "anomaly": round(total_anomaly / total, 3),
            "position": round(total_drift / total, 3),
            "boundary": round(avg_incoherence / total, 3),
        }

    @property
    def dominant_dimension(self) -> str:
        """Which emphasis dimension is strongest."""
        e = self.emphasis
        return max(e, key=e.get)

    @property
    def hot_words(self) -> list[WordAnalysis]:
        """Words with above-average energy (demand interpretive attention)."""
        if not self.words:
            return []
        avg = sum(w.energy for w in self.words) / len(self.words)
        return [w for w in self.words if w.energy > avg]

    @property
    def active_roots(self) -> list[tuple[str, float]]:
        """Roots in this verse ranked by weight. Returns (root_key, weight)."""
        roots = {}
        for w in self.words:
            if w.root_key and (w.root_key not in roots or w.weight > roots[w.root_key]):
                roots[w.root_key] = w.weight
        return sorted(roots.items(), key=lambda x: x[1], reverse=True)


def _instance_agreement(feats_a: dict, feats_b: dict) -> float:
    """Per-subspace agreement between two word instances.

    For each grammatical dimension where both words have a value,
    scores 1.0 if same, 0.0 if different. Averages across active dimensions.

    This is softer than cosine on one-hot vectors because:
    - Only counts dimensions where both words participate
    - "Both verbs in 3rd person perfect" scores high even if other features differ
    """
    subspace_keys = ["pos", "verb_form", "aspect", "person", "number", "gender", "case_value"]
    agreements = []
    for key in subspace_keys:
        val_a = feats_a.get(key)
        val_b = feats_b.get(key)
        if val_a and val_b:
            agreements.append(1.0 if val_a == val_b else 0.0)
    if not agreements:
        return 0.5  # no comparable features
    return float(np.mean(agreements))


def _profile_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Euclidean distance between two profile vectors, normalized to [0, 1]."""
    diff = a - b
    # Max possible distance is sqrt(2) for two unit-sum distributions
    raw = float(np.sqrt(np.dot(diff, diff)))
    return min(raw / 1.414, 1.0)


def _profile_cosine(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two profile vectors. Returns [0, 1]."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a < 1e-12 or norm_b < 1e-12:
        return 0.0
    return float(np.clip(np.dot(a, b) / (norm_a * norm_b), 0.0, 1.0))


def analyze_verse(
    word_data: list[dict],
    root_vectors: dict[int, RootVector],
) -> VerseAnalysis:
    """Analyze a verse's dynamics using distributional root vectors.

    Args:
        word_data: list of dicts, one per word, with keys:
            word_index, text, root_id (int or None),
            instance_features (dict with pos, verb_form, aspect, etc.)
        root_vectors: dict mapping root_id -> RootVector (pre-built)

    Returns:
        VerseAnalysis with per-word metrics and aggregate emphasis.
    """
    analyses = []
    prev_profile = None

    for i, wd in enumerate(word_data):
        root_id = wd.get("root_id")
        rv = root_vectors.get(root_id) if root_id else None

        # Weight: distributional centrality of this root
        weight = rv.distributional_weight if rv else 0.0

        # Anomaly: how unusual is this specific usage
        anomaly = instance_anomaly(rv, wd.get("instance_features", {})) if rv else 0.0

        # Current profile (use root's full profile, or zero for particles)
        curr_profile = rv.profile if rv else np.zeros(PROFILE_DIM)

        # Drift: profile distance from previous word
        if prev_profile is not None:
            drift = _profile_distance(prev_profile, curr_profile)
        else:
            drift = 0.0

        analyses.append(WordAnalysis(
            word_index=wd["word_index"],
            text=wd["text"],
            root_key=rv.lookup_key if rv else None,
            weight=round(weight, 4),
            anomaly=round(anomaly, 4),
            drift=round(drift, 4),
            coherence=None,  # filled in next pass
        ))

        prev_profile = curr_profile

    # Second pass: coherence with next ROOT-BEARING word.
    # Particles (no root) get coherence from the nearest root-bearing neighbors.
    # This avoids zero-vector cosine = 0 polluting the boundary signal.
    root_profiles = []  # (index, profile) for words that have roots
    for i, wd in enumerate(word_data):
        root_id = wd.get("root_id")
        rv = root_vectors.get(root_id) if root_id else None
        if rv is not None:
            root_profiles.append((i, rv.profile))

    for i in range(len(analyses)):
        # Find next root-bearing word after position i
        next_profile = None
        for idx, prof in root_profiles:
            if idx > i:
                next_profile = prof
                break

        if next_profile is None:
            analyses[i].coherence = 1.0  # no more roots ahead: no boundary
            continue

        # Current profile: use this word's root, or nearest previous root
        root_id_curr = word_data[i].get("root_id")
        rv_curr = root_vectors.get(root_id_curr) if root_id_curr else None
        if rv_curr is not None:
            p_curr = rv_curr.profile
        else:
            # Particle: find nearest previous root-bearing word
            p_curr = None
            for idx, prof in reversed(root_profiles):
                if idx < i:
                    p_curr = prof
                    break
            if p_curr is None:
                # No previous root either — can't compute coherence
                analyses[i].coherence = None
                continue

        analyses[i].coherence = round(_profile_cosine(p_curr, next_profile), 4)

    return VerseAnalysis(
        surah=word_data[0].get("surah", 0) if word_data else 0,
        ayah=word_data[0].get("ayah", 0) if word_data else 0,
        words=analyses,
    )


def verse_coherence(analysis_a: VerseAnalysis, analysis_b: VerseAnalysis,
                    root_vectors: dict[int, RootVector],
                    word_data_a: list[dict] | None = None,
                    word_data_b: list[dict] | None = None) -> float:
    """Coherence between two verses (inter-verse phase-lock).

    Combines three signals:
      1. Instance drift: cosine distance between the grammatical features
         of the last words of verse A and first words of verse B.
         This captures shifts in tense, person, mood — the actual boundary signal.
      2. Root profile drift: distributional distance between tail/head roots.
      3. Root overlap: Jaccard similarity of root sets (topic continuity).

    Returns value in [0, 1]: 1 = full coherence, 0 = hard boundary.
    """
    # Signal 1: Instance-level feature agreement (tail→head)
    # Measures: same person? same aspect? same POS type? across verse boundary.
    # Skip particles (CONJ, P, DET, etc.) — find the last/first CONTENT word.
    _PARTICLE_POS = {"CONJ", "P", "DET", "REM", "EMPH", "VOC", "SUB", "FUT",
                     "CIRC", "SUP", "RSLT", "INL", "CERT", "CAUS", "INT",
                     "AMD", "EXL", "SUR", "ANS", "EQ", "EXH", "INC", "PREV",
                     "AVR", "EXP", "PRO", "RES", "RET", "COM"}
    instance_coherence = 0.5
    if word_data_a and word_data_b:
        # Last content word of A
        tail_feats = None
        for wd in reversed(word_data_a):
            feats = wd.get("instance_features", {})
            if feats and feats.get("pos") not in _PARTICLE_POS:
                tail_feats = feats
                break
        # First content word of B
        head_feats = None
        for wd in word_data_b:
            feats = wd.get("instance_features", {})
            if feats and feats.get("pos") not in _PARTICLE_POS:
                head_feats = feats
                break
        if tail_feats is not None and head_feats is not None:
            instance_coherence = _instance_agreement(tail_feats, head_feats)

    # Signal 2: Root profile drift (tail→head)
    tail_profile = None
    for w in reversed(analysis_a.words):
        if w.root_key:
            for rv in root_vectors.values():
                if rv.lookup_key == w.root_key:
                    tail_profile = rv.profile
                    break
            if tail_profile is not None:
                break

    head_profile = None
    for w in analysis_b.words:
        if w.root_key:
            for rv in root_vectors.values():
                if rv.lookup_key == w.root_key:
                    head_profile = rv.profile
                    break
            if head_profile is not None:
                break

    if tail_profile is not None and head_profile is not None:
        root_coherence = _profile_cosine(tail_profile, head_profile)
    else:
        root_coherence = 0.5

    # Signal 3: Root set overlap (topic continuity)
    roots_a = {w.root_key for w in analysis_a.words if w.root_key}
    roots_b = {w.root_key for w in analysis_b.words if w.root_key}
    if roots_a or roots_b:
        jaccard = len(roots_a & roots_b) / len(roots_a | roots_b)
    else:
        jaccard = 0.0

    # Instance features are the primary boundary signal (50%),
    # root profiles secondary (30%), topic overlap tertiary (20%)
    return round(instance_coherence * 0.5 + root_coherence * 0.3 + jaccard * 0.2, 4)
