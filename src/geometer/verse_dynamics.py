"""
Verse Dynamics: PRISM-Native Sequence Analysis.

This module extends PRISM for verse-level dynamics analysis using
distributional root vectors. All computations use PRISM correlation
and can generate derivation certificates.

Four signals per word, grounded in Arabic linguistics:

  weight    = distributional_weight of the root (PRISM stratum-based)
  anomaly   = instance_anomaly using PRISM fidelity deviation
  drift     = profile distance using PRISM correlation
  coherence = adjacent word similarity using PRISM correlation
"""

from dataclasses import dataclass
from typing import Optional

from .root_space import (
    RootVector, instance_anomaly, PROFILE_DIM,
    _POS_IDX, _VF_IDX, _ASP_IDX, _PER_IDX, _NUM_IDX, _GEN_IDX, _CAS_IDX,
    POS_DIM, VF_DIM, ASP_DIM, PER_DIM, NUM_DIM, GEN_DIM, CAS_DIM,
    concordance_distance, root_correlation, derive_concordance,
    _profile_to_int, _features_to_int,
)
from .uor import Q256


@dataclass
class WordAnalysis:
    """Analysis of a single word in a verse."""
    word_index: int
    text: str
    root_key: Optional[str]
    weight: float
    anomaly: float
    drift: float
    coherence: Optional[float]
    prism_derivation_id: Optional[str] = None

    @property
    def energy(self) -> float:
        """Total energy = weight + anomaly + drift."""
        return self.weight + self.anomaly + self.drift


@dataclass
class VerseAnalysis:
    """Full analysis of a verse's dynamics."""
    surah: int
    ayah: int
    words: list
    prism_derivation_id: Optional[str] = None

    @property
    def emphasis(self) -> dict:
        """Emphasis profile: which dimension dominates this verse?"""
        if not self.words:
            return {"root": 0.25, "anomaly": 0.25, "position": 0.25, "boundary": 0.25}

        total_weight = sum(w.weight for w in self.words)
        total_anomaly = sum(w.anomaly for w in self.words)
        total_drift = sum(w.drift for w in self.words)

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
    def hot_words(self) -> list:
        """Words with above-average energy."""
        if not self.words:
            return []
        avg = sum(w.energy for w in self.words) / len(self.words)
        return [w for w in self.words if w.energy > avg]

    @property
    def active_roots(self) -> list:
        """Roots in this verse ranked by weight."""
        roots = {}
        for w in self.words:
            if w.root_key and (w.root_key not in roots or w.weight > roots[w.root_key]):
                roots[w.root_key] = w.weight
        return sorted(roots.items(), key=lambda x: x[1], reverse=True)


def _prism_profile_distance(profile_a: list, profile_b: list) -> float:
    """Profile distance using PRISM correlation."""
    coord_a = _profile_to_int(profile_a)
    coord_b = _profile_to_int(profile_b)
    correlation = Q256.correlate(coord_a, coord_b)
    return 1.0 - correlation['fidelity']


def _prism_instance_similarity(feats_a: dict, feats_b: dict) -> float:
    """Instance similarity using PRISM correlation."""
    coord_a = _features_to_int(feats_a)
    coord_b = _features_to_int(feats_b)
    correlation = Q256.correlate(coord_a, coord_b)
    return correlation['fidelity']


def _instance_agreement(feats_a: dict, feats_b: dict) -> float:
    """Per-subspace agreement between two word instances."""
    subspace_keys = ["pos", "verb_form", "aspect", "person", "number", "gender", "case_value"]
    agreements = []
    for key in subspace_keys:
        val_a = feats_a.get(key)
        val_b = feats_b.get(key)
        if val_a and val_b:
            agreements.append(1.0 if val_a == val_b else 0.0)
    if not agreements:
        return 0.5
    return sum(agreements) / len(agreements)


def _prism_profile_cosine(profile_a: list, profile_b: list) -> float:
    """Cosine similarity using PRISM fidelity."""
    coord_a = _profile_to_int(profile_a)
    coord_b = _profile_to_int(profile_b)
    correlation = Q256.correlate(coord_a, coord_b)
    return correlation['fidelity']


def analyze_verse(
    word_data: list,
    root_vectors: dict,
) -> VerseAnalysis:
    """Analyze a verse's dynamics using PRISM-native root vectors.

    All similarity computations use PRISM correlation.
    Generates derivation IDs for analyses.
    """
    analyses = []
    prev_profile = None
    prev_coord = None

    for i, wd in enumerate(word_data):
        root_id = wd.get("root_id")
        rv = root_vectors.get(root_id) if root_id else None

        weight = rv.distributional_weight if rv else 0.0
        anomaly = instance_anomaly(rv, wd.get("instance_features", {})) if rv else 0.0

        curr_profile = rv.profile if rv else [0.0] * PROFILE_DIM
        curr_coord = _profile_to_int(curr_profile) if rv else 0

        # Drift: PRISM distance from previous word
        if prev_coord is not None:
            correlation = Q256.correlate(prev_coord, curr_coord)
            drift = 1.0 - correlation['fidelity']
        else:
            drift = 0.0

        analyses.append(WordAnalysis(
            word_index=wd["word_index"],
            text=wd["text"],
            root_key=rv.lookup_key if rv else None,
            weight=round(weight, 4),
            anomaly=round(anomaly, 4),
            drift=round(drift, 4),
            coherence=None,
        ))

        prev_profile = curr_profile
        prev_coord = curr_coord

    # Second pass: coherence with next ROOT-BEARING word using PRISM
    root_profiles = []
    for i, wd in enumerate(word_data):
        root_id = wd.get("root_id")
        rv = root_vectors.get(root_id) if root_id else None
        if rv is not None:
            root_profiles.append((i, rv.profile, _profile_to_int(rv.profile)))

    for i in range(len(analyses)):
        next_profile = None
        next_coord = None
        for idx, prof, coord in root_profiles:
            if idx > i:
                next_profile = prof
                next_coord = coord
                break

        if next_profile is None:
            analyses[i].coherence = 1.0
            continue

        root_id_curr = word_data[i].get("root_id")
        rv_curr = root_vectors.get(root_id_curr) if root_id_curr else None
        if rv_curr is not None:
            p_curr = rv_curr.profile
            coord_curr = _profile_to_int(p_curr)
        else:
            p_curr = None
            coord_curr = None
            for idx, prof, coord in reversed(root_profiles):
                if idx < i:
                    p_curr = prof
                    coord_curr = coord
                    break
            if coord_curr is None:
                analyses[i].coherence = None
                continue

        # PRISM-based coherence
        correlation = Q256.correlate(coord_curr, next_coord)
        analyses[i].coherence = round(correlation['fidelity'], 4)

    return VerseAnalysis(
        surah=word_data[0].get("surah", 0) if word_data else 0,
        ayah=word_data[0].get("ayah", 0) if word_data else 0,
        words=analyses,
    )


def verse_coherence(
    analysis_a: VerseAnalysis,
    analysis_b: VerseAnalysis,
    root_vectors: dict,
    word_data_a: list = None,
    word_data_b: list = None,
) -> float:
    """PRISM-native coherence between two verses.

    Combines three signals using PRISM correlation:
      1. Instance feature drift (50%)
      2. Root profile drift (30%)
      3. Root overlap (20%)

    Returns value in [0, 1]: 1 = full coherence, 0 = hard boundary.
    """
    _PARTICLE_POS = {"CONJ", "P", "DET", "REM", "EMPH", "VOC", "SUB", "FUT",
                     "CIRC", "SUP", "RSLT", "INL", "CERT", "CAUS", "INT",
                     "AMD", "EXL", "SUR", "ANS", "EQ", "EXH", "INC", "PREV",
                     "AVR", "EXP", "PRO", "RES", "RET", "COM"}

    # Signal 1: PRISM instance-level feature agreement
    instance_coherence = 0.5
    if word_data_a and word_data_b:
        tail_feats = None
        for wd in reversed(word_data_a):
            feats = wd.get("instance_features", {})
            if feats and feats.get("pos") not in _PARTICLE_POS:
                tail_feats = feats
                break
        head_feats = None
        for wd in word_data_b:
            feats = wd.get("instance_features", {})
            if feats and feats.get("pos") not in _PARTICLE_POS:
                head_feats = feats
                break
        if tail_feats and head_feats:
            instance_coherence = _prism_instance_similarity(tail_feats, head_feats)

    # Signal 2: PRISM root profile coherence
    tail_profile = None
    tail_coord = None
    for w in reversed(analysis_a.words):
        if w.root_key:
            for rv in root_vectors.values():
                if rv.lookup_key == w.root_key:
                    tail_profile = rv.profile
                    tail_coord = _profile_to_int(rv.profile)
                    break
            if tail_profile is not None:
                break

    head_profile = None
    head_coord = None
    for w in analysis_b.words:
        if w.root_key:
            for rv in root_vectors.values():
                if rv.lookup_key == w.root_key:
                    head_profile = rv.profile
                    head_coord = _profile_to_int(rv.profile)
                    break
            if head_profile is not None:
                break

    if tail_coord is not None and head_coord is not None:
        correlation = Q256.correlate(tail_coord, head_coord)
        root_coherence = correlation['fidelity']
    else:
        root_coherence = 0.5

    # Signal 3: Root set overlap
    roots_a = {w.root_key for w in analysis_a.words if w.root_key}
    roots_b = {w.root_key for w in analysis_b.words if w.root_key}
    if roots_a or roots_b:
        jaccard = len(roots_a & roots_b) / len(roots_a | roots_b)
    else:
        jaccard = 0.0

    return round(instance_coherence * 0.5 + root_coherence * 0.3 + jaccard * 0.2, 4)


def derive_verse_analysis(analysis: VerseAnalysis, root_vectors: dict) -> dict:
    """Generate derivation certificate for a verse analysis.

    Creates PRISM derivations for all pairwise root similarities.
    """
    derivations = []

    for i in range(len(analysis.words) - 1):
        w1 = analysis.words[i]
        w2 = analysis.words[i + 1]

        if w1.root_key and w2.root_key:
            rv1 = None
            rv2 = None
            for rv in root_vectors.values():
                if rv.lookup_key == w1.root_key:
                    rv1 = rv
                if rv.lookup_key == w2.root_key:
                    rv2 = rv
                if rv1 and rv2:
                    break

            if rv1 and rv2:
                result = derive_concordance(rv1, rv2)
                derivations.append({
                    'word_pair': (w1.text, w2.text),
                    'roots': (w1.root_key, w2.root_key),
                    'derivation_id': result['derivation'].derivation_id if result['derivation'] else None,
                    'distance': result['distance'],
                    'fidelity': result['correlation']['fidelity'],
                })

    return {
        'verse': f"{analysis.surah}:{analysis.ayah}",
        'derivation_count': len(derivations),
        'derivations': derivations,
    }
