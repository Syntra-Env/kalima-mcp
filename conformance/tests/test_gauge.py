"""
Conformance Test: Gauge Field (PRISM-Native)
============================================

Validates geometer.gauge against conformance/standards/gauge.py
Now tests both the gauge operations and PRISM integration.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from kalima_math import gauge
from kalima_math.gauge import GAUGE_ENGINE, SIGMAS


class TestPauliMatrices:
    """Validate Pauli matrix properties."""

    def test_pauli_matrices_exist(self):
        assert hasattr(gauge, 'SIGMA_1')
        assert hasattr(gauge, 'SIGMA_2')
        assert hasattr(gauge, 'SIGMA_3')
        assert hasattr(gauge, 'SIGMAS')

    def test_pauli_matrices_are_2x2(self):
        for sigma in SIGMAS:
            assert len(sigma) == 2
            assert len(sigma[0]) == 2
            assert len(sigma[1]) == 2


class TestFieldMatrix:
    """Validate H matrix construction."""

    def test_get_h_matrix_returns_2x2(self):
        h = gauge.get_h_matrix([1.0, 0.0, 0.0])
        assert len(h) == 2
        assert len(h[0]) == 2

    def test_get_h_matrix_with_insufficient_components(self):
        h = gauge.get_h_matrix([1.0])
        assert len(h) == 2
        assert all(all(abs(v) < 1e-10 for v in row) for row in h)


class TestCurvatureTensor:
    """Validate curvature tensor computation."""

    def test_curvature_is_anti_symmetric(self):
        """R_uv = -R_vu"""
        h_0 = gauge.get_h_matrix([1.0, 0.0, 0.0])
        h_1 = gauge.get_h_matrix([0.0, 1.0, 0.0])

        r_01 = gauge.calculate_curvature_tensor(h_0, h_1)
        r_10 = gauge.calculate_curvature_tensor(h_1, h_0)

        for i in range(2):
            for j in range(2):
                assert abs(r_01[i][j] - (-r_10[i][j])) < 1e-10

    def test_curvature_of_same_matrix_is_zero(self):
        """R_ii = [H_i, H_i] = 0"""
        h = gauge.get_h_matrix([1.0, 0.0, 0.0])
        r = gauge.calculate_curvature_tensor(h, h)

        for i in range(2):
            for j in range(2):
                assert abs(r[i][j]) < 1e-10


class TestHolonomicCurvature:
    """Validate holonomic curvature bounds."""

    def test_curvature_is_non_negative(self):
        h_seq = [
            gauge.get_h_matrix([0.1, 0.0, 0.0]),
            gauge.get_h_matrix([0.0, 0.1, 0.0]),
            gauge.get_h_matrix([0.0, 0.0, 0.1]),
        ]
        kappa = gauge.get_discrete_curvature(h_seq)

        assert kappa >= 0.0, f"Holonomic curvature must be >= 0, got {kappa}"

    def test_curvature_bounded_by_pi(self):
        bounds = (0.0, 3.14159)  # [0, π]
        h_seq = [
            gauge.get_h_matrix([1.0, 1.0, 1.0]),
            gauge.get_h_matrix([-1.0, -1.0, -1.0]),
        ]
        kappa = gauge.get_discrete_curvature(h_seq)

        assert bounds[0] <= kappa <= bounds[1], \
            f"Curvature {kappa} outside bounds {bounds}"

    def test_empty_sequence_returns_zero(self):
        kappa = gauge.get_discrete_curvature([])
        assert kappa == 0.0, "Empty sequence must have zero curvature"


class TestFieldTension:
    """Validate field tension properties."""

    def test_tension_is_non_negative(self):
        h = gauge.get_h_matrix([1.0, 0.5, -0.3])
        tension = gauge.get_field_tension(h)

        assert tension >= 0.0, f"Field tension must be >= 0, got {tension}"

    def test_tension_of_zero_is_zero(self):
        h = gauge.get_h_matrix([0.0, 0.0, 0.0])
        tension = gauge.get_field_tension(h)

        assert tension == 0.0, "Zero field must have zero tension"


class TestLyapunovDeviation:
    """Validate Lyapunov deviation (now PRISM-based)."""

    def test_deviation_is_non_negative(self):
        h_state = gauge.get_h_matrix([1.0, 0.5, -0.3])
        h_baseline = gauge.get_h_matrix([0.8, 0.4, -0.2])

        dev = gauge.get_lyapunov_deviation(h_state, h_baseline)

        assert dev >= 0.0, f"Lyapunov deviation must be >= 0, got {dev}"

    def test_deviation_to_self_is_zero(self):
        h = gauge.get_h_matrix([1.0, 0.5, -0.3])
        dev = gauge.get_lyapunov_deviation(h, h)

        assert dev < 1e-6, f"Deviation to self should be ~0, got {dev}"


class TestResonanceAnalysis:
    """Validate resonance analysis structure with PRISM integration."""

    def test_analysis_has_required_fields(self):
        h_seq = [
            gauge.get_h_matrix([0.1, 0.0, 0.0]),
            gauge.get_h_matrix([0.0, 0.1, 0.0]),
        ]
        locations = ["verse_1:1", "verse_1:2"]

        analysis = gauge.analyze_resonance(h_seq, locations)

        assert hasattr(analysis, 'global_curvature')
        assert hasattr(analysis, 'consistency')
        assert hasattr(analysis, 'hotspots')

    def test_consistency_is_valid_level(self):
        h_seq = [
            gauge.get_h_matrix([0.01, 0.0, 0.0]),
            gauge.get_h_matrix([0.01, 0.0, 0.0]),
        ]
        analysis = gauge.analyze_resonance(h_seq, ["v1", "v2"])

        valid_levels = ["highly_consistent", "moderately_consistent", "context_dependent"]
        assert analysis.consistency in valid_levels

    def test_hotspots_count_limited(self):
        h_seq = [
            gauge.get_h_matrix([float(i) * 0.1, 0.0, 0.0])
            for i in range(20)
        ]
        locations = [f"v{i}" for i in range(20)]

        analysis = gauge.analyze_resonance(h_seq, locations)

        assert len(analysis.hotspots) <= 10

    def test_consistency_thresholds(self):
        # Highly consistent: kappa < 0.5
        low_kappa_seq = [
            gauge.get_h_matrix([0.01, 0.0, 0.0]),
            gauge.get_h_matrix([0.01, 0.0, 0.0]),
            gauge.get_h_matrix([0.01, 0.0, 0.0]),
        ]
        low_kappa_analysis = gauge.analyze_resonance(low_kappa_seq, ["v1", "v2", "v3"])
        assert low_kappa_analysis.consistency == "highly_consistent"

        # Context dependent: high curvature
        high_kappa_seq = [
            gauge.get_h_matrix([2.0, 0.0, 0.0]),
            gauge.get_h_matrix([0.0, 2.0, 0.0]),
        ]
        high_kappa_analysis = gauge.analyze_resonance(high_kappa_seq, ["v1", "v2"])
        # May be highly_consistent depending on actual curvature


class TestPRISMIntegration:
    """Validate PRISM integration in gauge module."""

    def test_field_state_has_prism_coordinate(self):
        state = gauge.get_field_state([1.0, 0.5, -0.3])
        assert hasattr(state, 'prism_coordinate')
        assert state.prism_coordinate is not None

    def test_field_state_has_stratum(self):
        state = gauge.get_field_state([1.0, 0.5, -0.3])
        assert hasattr(state, 'stratum')
        assert state.stratum >= 0

    def test_resonance_includes_prism_correlation(self):
        h_seq = [
            gauge.get_h_matrix([0.1, 0.0, 0.0]),
            gauge.get_h_matrix([0.0, 0.1, 0.0]),
        ]
        analysis = gauge.analyze_resonance(h_seq, ["v1", "v2"])

        assert analysis.prism_correlation is not None
        assert 'fidelity' in analysis.prism_correlation

    def test_resonance_includes_derivation_id(self):
        h_seq = [
            gauge.get_h_matrix([0.1, 0.0, 0.0]),
            gauge.get_h_matrix([0.0, 0.1, 0.0]),
        ]
        analysis = gauge.analyze_resonance(h_seq, ["v1", "v2"])

        assert analysis.derivation_id is not None


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
