"""Geometer Conformance Tests.

These tests validate that the implementation conforms to the standards
defined in conformance/standards/.
"""

from .test_uor_ring import *
from .test_root_space import *
from .test_gauge import *

__all__ = [
    "TestRingParameters",
    "TestRingGenerators",
    "TestCoreIdentities",
    "TestMetricBounds",
    "TestDihedralOrbit",
    "TestFiberDecomposition",
    "TestStratum",
    "TestProfileDimensions",
    "TestRootVectorConstruction",
    "TestDistributionalWeight",
    "TestAnomalyScore",
    "TestConcordanceDistance",
    "TestSurahCoverage",
    "TestPauliMatrices",
    "TestFieldMatrix",
    "TestCurvatureTensor",
    "TestHolonomicCurvature",
    "TestFieldTension",
    "TestLyapunovDeviation",
    "TestResonanceAnalysis",
]
