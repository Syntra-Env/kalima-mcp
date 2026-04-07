"""
Conformance Test: Semantic Axioms
=================================

Validates geometer.semantic_axioms against the paper:
"The Mathematical Expressions of Quranic Exegeses"

Key theorems tested:
  - Tadabor Theorem: |M| = 892,164
  - Theorem 1: Verse space is a complex vector space
  - Theorem 2: Fuzzy root meaning as membership function
  - Theorem 3: Root independence as orthogonality
  - Definition 5: Theoretical Verse Space TV ⊂ ℂⁿ
  - Definition 7: Fuzzy root meaning μ_R: TV → [0,1]
"""

import sys
import os
import math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from geometer.semantic_axioms import (
    TadaborPosition,
    TheoreticalVerseSpace,
    FuzzyRootMeaning,
    RootIndependence,
    TafsirAlgebra,
    SemanticCurvature,
    ThemeClosure,
    VerseVector,
    SemanticConformance,
    TADABOR_POSITION_COUNT,
    TADABOR_VERSE_COUNT,
    TADABOR_SURAH_COUNT,
)


class TestTadaborTheorem:
    """Test Tadabor Theorem: |M| = 7,826 × 114 = 892,164"""

    def test_position_count(self):
        """Total positions must equal Tadabor count."""
        expected = TADABOR_VERSE_COUNT * TADABOR_SURAH_COUNT
        assert TADABOR_POSITION_COUNT == expected

    def test_position_index_bounds(self):
        """Position index must be in [0, 892,163]."""
        pos = TadaborPosition(114, TADABOR_VERSE_COUNT, 0)
        assert 0 <= pos.tadabor_index < TADABOR_POSITION_COUNT

    def test_verse_label_format(self):
        """Verse label must be 'surah:ayah' format."""
        pos = TadaborPosition(5, 23, 7)
        assert pos.verse_label == "5:23"


class TestVerseSpace:
    """Test Theoretical Verse Space TV ⊂ ℂ²"""

    def test_complex_amplitudes(self):
        """Verse space must use complex amplitudes."""
        tv = TheoreticalVerseSpace(1+0j, 0+0j)
        assert isinstance(tv.amplitude_positive, complex)
        assert isinstance(tv.amplitude_negative, complex)

    def test_inner_product_is_complex(self):
        """Inner product must return complex number."""
        tv_a = TheoreticalVerseSpace(1+0j, 0+0j)
        tv_b = TheoreticalVerseSpace(0+0j, 1+0j)
        ip = tv_a.inner_product(tv_b)
        assert isinstance(ip, complex)

    def test_fidelity_bounded(self):
        """Fidelity must be in [0, 1]."""
        tv_a = TheoreticalVerseSpace(1+0j, 0+0j)
        tv_b = TheoreticalVerseSpace(1+0j, 0+0j)
        fidelity = tv_a.fidelity(tv_b)
        assert 0.0 <= fidelity <= 1.0

    def test_identical_states_have_fidelity_one(self):
        """Identical states must have fidelity = 1."""
        tv_a = TheoreticalVerseSpace(1+0j, 0+0j)
        tv_b = TheoreticalVerseSpace(1+0j, 0+0j)
        assert abs(tv_a.fidelity(tv_b) - 1.0) < 1e-10

    def test_orthogonal_states_have_fidelity_zero(self):
        """Orthogonal states must have fidelity = 0."""
        tv_a = TheoreticalVerseSpace(1+0j, 0+0j)
        tv_b = TheoreticalVerseSpace(0+0j, 1+0j)
        assert tv_a.fidelity(tv_b) < 1e-10


class TestFuzzyRootMeaning:
    """Test fuzzy root meaning μ_R: TV → [0,1]"""

    def test_membership_bounded(self):
        """Membership must be in [0, 1]."""
        tv_center = TheoreticalVerseSpace(1+0j, 0+0j)
        fuzzy = FuzzyRootMeaning(root_id=1, cluster_center=tv_center)
        tv_verse = TheoreticalVerseSpace(0.5+0j, 0.5+0j)
        membership = fuzzy.membership(tv_verse)
        assert 0.0 <= membership <= 1.0

    def test_center_has_full_membership(self):
        """Membership at cluster center must be ~1."""
        tv_center = TheoreticalVerseSpace(1+0j, 0+0j)
        fuzzy = FuzzyRootMeaning(root_id=1, cluster_center=tv_center)
        assert abs(fuzzy.membership(tv_center) - 1.0) < 1e-10

    def test_semantic_distance_bounded(self):
        """Semantic distance must be in [0, 1]."""
        tv_center = TheoreticalVerseSpace(1+0j, 0+0j)
        fuzzy = FuzzyRootMeaning(root_id=1, cluster_center=tv_center)
        tv_verse = TheoreticalVerseSpace(0+0j, 1+0j)
        dist = fuzzy.semantic_distance(tv_verse)
        assert 0.0 <= dist <= 1.0


class TestRootIndependence:
    """Test root independence: orthogonal ⟺ independent"""

    def test_orthogonal_are_independent(self):
        """Orthogonal roots must be independent."""
        tv_a = TheoreticalVerseSpace(1+0j, 0+0j)
        tv_b = TheoreticalVerseSpace(0+0j, 1+0j)
        assert RootIndependence.are_independent(tv_a, tv_b)

    def test_identical_not_independent(self):
        """Identical roots must not be independent."""
        tv_a = TheoreticalVerseSpace(1+0j, 0+0j)
        tv_b = TheoreticalVerseSpace(1+0j, 0+0j)
        assert not RootIndependence.are_independent(tv_a, tv_b)

    def test_independence_degree_bounded(self):
        """Independence degree must be in [0, 1]."""
        tv_a = TheoreticalVerseSpace(1+0j, 0+0j)
        tv_b = TheoreticalVerseSpace(0+0j, 1+0j)
        degree = RootIndependence.independence_degree(tv_a, tv_b)
        assert 0.0 <= degree <= 1.0


class TestTafsirAlgebra:
    """Test tafsir algebra τ = {τ₁, τ₂, τ₃}"""

    def test_three_components(self):
        """Tafsir algebra must have exactly 3 components."""
        tau = TafsirAlgebra((1.0, 0.5, 0.3))
        assert len(tau.components) == 3

    def test_literal_is_zahir(self):
        """Literal tafsir corresponds to zahir (external)."""
        tau = TafsirAlgebra.literal()
        assert tau.components[0] > tau.components[1]
        assert tau.components[0] > tau.components[2]

    def test_interpretive_is_batin(self):
        """Interpretive tafsir corresponds to batin (internal)."""
        tau = TafsirAlgebra.interpretive()
        assert tau.components[1] > tau.components[0]
        assert tau.components[1] > tau.components[2]

    def test_apply_preserves_norm(self):
        """Applying tafsir should preserve state norm."""
        tau = TafsirAlgebra((0.1, 0.2, 0.3))
        tv = TheoreticalVerseSpace(1+0j, 0+0j)
        result = tau.apply(tv)
        assert abs(result.norm - tv.norm) < 1e-10


class TestSemanticCurvature:
    """Test semantic curvature as discontinuity measure"""

    def test_curvature_bounded(self):
        """Curvature must be in [0, 1]."""
        states = [
            TheoreticalVerseSpace(1+0j, 0+0j),
            TheoreticalVerseSpace(0+0j, 1+0j),
        ]
        kappa = SemanticCurvature.from_states(states)
        assert 0.0 <= kappa <= 1.0

    def test_identical_states_have_zero_curvature(self):
        """Identical states must have zero curvature."""
        states = [
            TheoreticalVerseSpace(1+0j, 0+0j),
            TheoreticalVerseSpace(1+0j, 0+0j),
            TheoreticalVerseSpace(1+0j, 0+0j),
        ]
        kappa = SemanticCurvature.from_states(states)
        assert kappa < 1e-10

    def test_boundary_classification(self):
        """Boundary type must be valid string."""
        kappa = 0.6
        btype = SemanticCurvature.boundary_type(kappa)
        assert btype in ["continuity", "transition", "shift", "break"]

    def test_is_boundary(self):
        """Boundary detection must work correctly."""
        assert SemanticCurvature.is_boundary(0.6, threshold=0.5)
        assert not SemanticCurvature.is_boundary(0.3, threshold=0.5)


class TestThemeClosure:
    """Test theme closure as holonomy semantics"""

    def test_closure_degree_bounded(self):
        """Closure degree must be in [0, 1]."""
        tv_a = TheoreticalVerseSpace(1+0j, 0+0j)
        tv_b = TheoreticalVerseSpace(0+0j, 1+0j)
        closure = ThemeClosure.closure_degree(tv_a, tv_b)
        assert 0.0 <= closure <= 1.0

    def test_identical_has_zero_closure(self):
        """Identical states have zero closure."""
        tv = TheoreticalVerseSpace(1+0j, 0+0j)
        closure = ThemeClosure.closure_degree(tv, tv)
        assert closure < 1e-10

    def test_is_resolved(self):
        """Theme resolution detection must work."""
        assert ThemeClosure.is_resolved(0.05, threshold=0.1)
        assert not ThemeClosure.is_resolved(0.5, threshold=0.1)


class TestVerseVector:
    """Test verse vector as composition of roots"""

    def test_composition_from_roots(self):
        """Verse must compose from root states."""
        verse = VerseVector([
            (1, 0.5, TheoreticalVerseSpace(1+0j, 0+0j)),
            (2, 0.5, TheoreticalVerseSpace(0+0j, 1+0j)),
        ])
        assert len(verse.root_states) == 2

    def test_meaning_coherence_bounded(self):
        """Meaning coherence must be in [0, 1]."""
        verse = VerseVector([
            (1, 0.5, TheoreticalVerseSpace(1+0j, 0+0j)),
            (2, 0.5, TheoreticalVerseSpace(0+0j, 1+0j)),
        ])
        coherence = verse.meaning_coherence()
        assert 0.0 <= coherence <= 1.0


class TestSemanticConformance:
    """Test semantic conformance checker"""

    def test_check_tadabor_size(self):
        """Tadabor size check must pass."""
        passed, msg = SemanticConformance.check_tadabor_size(list(range(TADABOR_POSITION_COUNT)))
        assert passed

    def test_check_verse_normalization(self):
        """Verse normalization check."""
        verse = VerseVector([
            (1, 0.5, TheoreticalVerseSpace(1+0j, 0+0j)),
        ])
        passed, msg = SemanticConformance.check_verse_normalization(verse)
        assert passed

    def test_check_membership(self):
        """Membership check must pass for valid values."""
        passed, msg = SemanticConformance.check_fuzzy_membership(0.75)
        assert passed

    def test_full_conformance(self):
        """Full conformance check."""
        verse = VerseVector([
            (1, 0.5, TheoreticalVerseSpace(1+0j, 0+0j)),
        ])
        result = SemanticConformance.full_conformance_check(verse, 0.75)
        assert "passed" in result
        assert "checks" in result


class TestAxiomsReference:
    """Verify axioms reference the paper correctly"""

    def test_tadabor_count(self):
        """Tadabor count must be exactly 892,164."""
        assert TADABOR_POSITION_COUNT == 892164

    def test_verse_count(self):
        """Verse count must be 7,826."""
        assert TADABOR_VERSE_COUNT == 7826

    def test_surah_count(self):
        """Surah count must be 114."""
        assert TADABOR_SURAH_COUNT == 114


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
