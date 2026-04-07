"""
Conformance Test: Root Space (PRISM-Native)
===========================================

Validates geometer.root_space against conformance/standards/root_space.py
All computations now use PRISM correlation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from geometer.root_space import (
    RootVector,
    build_root_vector,
    instance_anomaly,
    concordance_distance,
    root_correlation,
    PROFILE_DIM,
    concordance_distance,
    _profile_to_int,
)
from conformance.standards import (
    TOTAL_PROFILE_DIM,
    MAX_SURAHS,
)


class TestProfileDimensions:
    """Validate profile dimension conformance."""

    def test_profile_dim_matches_standard(self):
        from geometer.root_space import POS_DIM, VF_DIM, ASP_DIM, PER_DIM, NUM_DIM, GEN_DIM, CAS_DIM
        expected = POS_DIM + VF_DIM + ASP_DIM + PER_DIM + NUM_DIM + GEN_DIM + CAS_DIM
        assert PROFILE_DIM == expected


class TestRootVectorConstruction:
    """Validate RootVector building with PRISM integration."""

    def test_build_root_vector_with_valid_data(self):
        morpheme_features = [
            {"pos": "V", "verb_form": "(I)", "aspect": "PERF",
             "person": "3", "number": "S", "gender": "M", "case_value": "NOM"},
        ]
        locations = [(1, 1), (1, 2)]

        rv = build_root_vector(
            root_id=1,
            lookup_key="كتب",
            label_ar="K-T-B",
            morpheme_features=morpheme_features,
            instance_locations=locations,
        )

        assert rv.root_id == 1
        assert rv.lookup_key == "كتب"
        assert rv.total_instances == 2
        assert rv.total_verses == 2
        assert rv.total_morpheme_types == 1

    def test_profile_is_normalized(self):
        morpheme_features = [
            {"pos": "V", "verb_form": "(I)", "aspect": "PERF",
             "person": "3", "number": "S", "gender": "M", "case_value": "NOM"},
            {"pos": "N", "verb_form": "(I)", "aspect": "PERF",
             "person": "3", "number": "S", "gender": "M", "case_value": "ACC"},
        ]
        locations = [(1, 1), (1, 2)]

        rv = build_root_vector(
            root_id=1,
            lookup_key="كتب",
            label_ar="K-T-B",
            morpheme_features=morpheme_features,
            instance_locations=locations,
        )

        total = sum(rv.profile)
        assert abs(total - 1.0) < 1e-10, \
            f"Profile must be normalized, got sum = {total}"

    def test_profile_is_non_negative(self):
        morpheme_features = [
            {"pos": "V", "verb_form": "(I)", "aspect": "PERF"},
        ]
        rv = build_root_vector(
            root_id=1,
            lookup_key="كتب",
            label_ar="K-T-B",
            morpheme_features=morpheme_features,
            instance_locations=[(1, 1)],
        )

        assert all(p >= 0 for p in rv.profile), \
            "All profile values must be non-negative"


class TestDistributionalWeight:
    """Validate distributional weight bounds."""

    def test_weight_is_bounded_0_to_1(self):
        morpheme_features = [
            {"pos": "V", "verb_form": "(I)", "aspect": "PERF"},
        ]
        rv = build_root_vector(
            root_id=1,
            lookup_key="كتب",
            label_ar="K-T-B",
            morpheme_features=morpheme_features,
            instance_locations=[(1, 1)],
        )

        w = rv.distributional_weight
        assert 0.0 <= w <= 1.0, \
            f"Distributional weight must be in [0, 1], got {w}"

    def test_empty_root_has_zero_weight(self):
        rv = RootVector(
            root_id=0,
            lookup_key="",
            label_ar=None,
        )

        assert rv.distributional_weight == 0.0, \
            "Empty root must have zero distributional weight"


class TestAnomalyScore:
    """Validate anomaly score bounds (now PRISM-based)."""

    def test_anomaly_is_bounded_0_to_1(self):
        morpheme_features = [
            {"pos": "V", "verb_form": "(I)", "aspect": "PERF",
             "person": "3", "number": "S", "gender": "M", "case_value": "NOM"},
        ]
        rv = build_root_vector(
            root_id=1,
            lookup_key="كتب",
            label_ar="K-T-B",
            morpheme_features=morpheme_features,
            instance_locations=[(1, 1)],
        )

        instance_features = {"pos": "V", "verb_form": "(I)", "aspect": "PERF",
                           "person": "3", "number": "S", "gender": "M", "case_value": "NOM"}
        a = instance_anomaly(rv, instance_features)

        assert 0.0 <= a <= 1.0, f"Anomaly score must be in [0, 1], got {a}"

    def test_identical_features_have_low_anomaly(self):
        """Identical features should have very low anomaly."""
        morpheme_features = [
            {"pos": "V", "verb_form": "(I)", "aspect": "PERF",
             "person": "3", "number": "S", "gender": "M", "case_value": "NOM"},
        ]
        rv = build_root_vector(
            root_id=1,
            lookup_key="كتب",
            label_ar="K-T-B",
            morpheme_features=morpheme_features,
            instance_locations=[(1, 1)],
        )

        instance_features = {"pos": "V", "verb_form": "(I)", "aspect": "PERF"}
        a = instance_anomaly(rv, instance_features)

        assert a < 0.1, f"Identical features should have low anomaly, got {a}"


class TestConcordanceDistance:
    """Validate concordance distance properties (now PRISM-based)."""

    def test_distance_is_symmetric(self):
        morphemes_a = [{"pos": "V", "verb_form": "(I)"}]
        morphemes_b = [{"pos": "N"}]

        rv_a = build_root_vector(1, "كتب", "A", morphemes_a, [(1, 1)])
        rv_b = build_root_vector(2, "قرأ", "B", morphemes_b, [(1, 2)])

        d_ab = concordance_distance(rv_a, rv_b)
        d_ba = concordance_distance(rv_b, rv_a)

        assert abs(d_ab - d_ba) < 1e-10, \
            f"Distance must be symmetric: d(a,b)={d_ab}, d(b,a)={d_ba}"

    def test_distance_to_self_is_zero(self):
        morphemes = [{"pos": "V", "verb_form": "(I)"}]
        rv = build_root_vector(1, "كتب", "A", morphemes, [(1, 1)])

        d = concordance_distance(rv, rv)

        assert d < 1e-6, f"Distance to self should be ~0, got {d}"

    def test_distance_is_bounded_0_to_1(self):
        morphemes_a = [{"pos": "V", "verb_form": "(I)"}]
        morphemes_b = [{"pos": "N"}]

        rv_a = build_root_vector(1, "كتب", "A", morphemes_a, [(1, 1)])
        rv_b = build_root_vector(2, "قرأ", "B", morphemes_b, [(1, 2)])

        d = concordance_distance(rv_a, rv_b)

        assert 0.0 <= d <= 1.0, f"Distance must be in [0, 1], got {d}"


class TestPRISMIntegration:
    """Validate PRISM integration in root_space."""

    def test_root_has_prism_coordinate(self):
        morphemes = [{"pos": "V", "verb_form": "(I)"}]
        rv = build_root_vector(1, "كتب", "A", morphemes, [(1, 1)])

        assert hasattr(rv, 'prism_coordinate')
        assert rv.prism_coordinate is not None

    def test_root_has_prism_triplet(self):
        morphemes = [{"pos": "V", "verb_form": "(I)"}]
        rv = build_root_vector(1, "كتب", "A", morphemes, [(1, 1)])

        assert hasattr(rv, 'prism_triplet')
        triad = rv.prism_triplet
        assert hasattr(triad, 'datum')
        assert hasattr(triad, 'stratum')
        assert hasattr(triad, 'spectrum')

    def test_profile_encodes_to_int(self):
        profile = [0.0] * PROFILE_DIM
        profile[0] = 1.0
        coord = _profile_to_int(profile)
        assert isinstance(coord, int)
        assert coord >= 0


class TestSurahCoverage:
    """Validate Quranic bounds."""

    def test_surahs_cannot_exceed_114(self):
        morpheme_features = [{"pos": "V"}]
        locations = [(i, 1) for i in range(1, 115)]
        rv = build_root_vector(
            root_id=1,
            lookup_key="كتب",
            label_ar="K-T-B",
            morpheme_features=morpheme_features,
            instance_locations=locations,
        )

        assert rv.total_surahs <= MAX_SURAHS, \
            f"Cannot have more than {MAX_SURAHS} surahs, got {rv.total_surahs}"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
