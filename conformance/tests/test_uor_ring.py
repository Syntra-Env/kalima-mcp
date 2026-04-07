"""
Conformance Test: UOR Ring Substrate
====================================

Validates geometer.uor against conformance/standards/uor_ring.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from kalima_math import uor
from conformance.standards import (
    RING_QUANTUM,
    MODULUS,
    MASK,
    REQUIRED_GENERATORS,
    CORE_IDENTITIES,
    DIHEDRAL_ORBIT_SIZE,
    FIBER_COUNT,
    TEST_ELEMENTS,
)
from conformance.standards.uor_ring import METRIC_BOUNDS as RING_METRIC_BOUNDS


class TestRingParameters:
    """Validate ring parameter conformance."""

    def test_ring_quantum_is_256(self):
        assert RING_QUANTUM == 256, f"Ring quantum must be 256, got {RING_QUANTUM}"

    def test_modulus_is_2_pow_256(self):
        expected = 2**256
        assert MODULUS == expected, f"Modulus must be 2^256, got {MODULUS}"

    def test_mask_is_mod_minus_1(self):
        expected = MODULUS - 1
        assert MASK == expected, f"MASK must be MODULUS - 1, got {MASK}"


class TestRingGenerators:
    """Validate dihedral group generators."""

    def test_neg_is_available(self):
        assert hasattr(uor, 'neg'), "neg generator must exist"

    def test_bnot_is_available(self):
        assert hasattr(uor, 'bnot'), "bnot generator must exist"

    def test_succ_is_available(self):
        assert hasattr(uor, 'succ'), "succ generator must exist"


class TestCoreIdentities:
    """Validate fundamental UOR identities (MUST hold for ALL x)."""

    def test_neg_bnot_equals_succ(self):
        """Core UOR identity: neg(bnot(x)) == succ(x)"""
        for x in TEST_ELEMENTS:
            result = uor.neg(uor.bnot(x))
            expected = uor.succ(x)
            assert result == expected, f"neg(bnot({x})) = {result}, expected {expected}"

    def test_neg_is_involution(self):
        """neg(neg(x)) == x"""
        for x in TEST_ELEMENTS:
            result = uor.neg(uor.neg(x))
            assert result == x, f"neg(neg({x})) = {result}, expected {x}"

    def test_bnot_is_involution(self):
        """bnot(bnot(x)) == x"""
        for x in TEST_ELEMENTS:
            result = uor.bnot(uor.bnot(x))
            assert result == x, f"bnot(bnot({x})) = {result}, expected {x}"

    def test_successor_wraps_correctly(self):
        """succ(succ(...(x)...)) wraps at MODULUS"""
        assert uor.succ(MASK) == 0, "succ(max) must wrap to 0"
        assert uor.succ(0) == 1, "succ(0) must be 1"


class TestMetricBounds:
    """Validate metric functions return values within defined bounds."""

    def test_hamming_distance_bounds(self):
        bounds = RING_METRIC_BOUNDS["hamming_distance"]
        for x in TEST_ELEMENTS:
            for y in TEST_ELEMENTS:
                d = uor.dist_hamming(x, y)
                assert bounds[0] <= d <= bounds[1], \
                    f"d_H({x}, {y}) = {d} outside bounds {bounds}"

    def test_ring_distance_bounds(self):
        bounds = RING_METRIC_BOUNDS["ring_distance"]
        for x in TEST_ELEMENTS:
            for y in TEST_ELEMENTS:
                d = uor.dist_ring(x, y)
                assert bounds[0] <= d <= bounds[1], \
                    f"d_R({x}, {y}) = {d} outside bounds {bounds}"

    def test_incompatibility_is_normalized(self):
        bounds = RING_METRIC_BOUNDS["incompatibility"]
        for x in TEST_ELEMENTS:
            for y in TEST_ELEMENTS:
                d = uor.get_incompatibility(x, y)
                assert bounds[0] <= d <= bounds[1], \
                    f"d_Δ({x}, {y}) = {d} outside normalized bounds {bounds}"


class TestDihedralOrbit:
    """Validate dihedral orbit structure."""

    def test_orbit_size_is_4(self):
        """Dihedral orbit must have exactly 4 elements."""
        for x in TEST_ELEMENTS:
            orbit = uor.get_dihedral_orbit(x)
            assert len(orbit) == DIHEDRAL_ORBIT_SIZE, \
                f"Orbit of {x} has {len(orbit)} elements, expected {DIHEDRAL_ORBIT_SIZE}"

    def test_orbit_contains_identity(self):
        """Orbit must contain the identity element."""
        for x in TEST_ELEMENTS:
            orbit = uor.get_dihedral_orbit(x)
            assert orbit["identity"] == x, \
                f"Orbit identity of {x} is {orbit['identity']}, expected {x}"


class TestFiberDecomposition:
    """Validate Z/2Z fiber decomposition."""

    def test_fiber_count_is_256(self):
        """Must decompose into exactly 256 fibers."""
        for x in TEST_ELEMENTS:
            fibers = uor.decompose_fibers(x)
            assert len(fibers) == FIBER_COUNT, \
                f"Fibers of {x} has {len(fibers)} elements, expected {FIBER_COUNT}"

    def test_fibers_are_binary(self):
        """Each fiber element must be 0 or 1."""
        for x in TEST_ELEMENTS:
            fibers = uor.decompose_fibers(x)
            for i, f in enumerate(fibers):
                assert f in (0, 1), f"Fiber {i} of {x} is {f}, not binary"


class TestStratum:
    """Validate stratum (popcount-based in PRISM)."""

    def test_stratum_of_zero_is_zero(self):
        """PRISM stratum of 0 is 0 (total popcount across all bytes)."""
        assert uor.get_stratum(0) == 0, "stratum(0) must be 0 in PRISM"

    def test_stratum_is_non_negative(self):
        """Stratum must be non-negative."""
        for x in TEST_ELEMENTS:
            v = uor.get_stratum(x)
            assert v >= 0, f"v_2({x}) = {v} is negative"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
