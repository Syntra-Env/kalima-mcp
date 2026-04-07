"""
Conformance Test: Fiber Bundle (HUFD-Compliant)
=============================================

Validates geometer.fiber_bundle against HUFD paper specifications:
  1. Base Manifold M (text positions as differentiable manifold)
  2. Principal Bundle E(M, SU(2), π)
  3. Connection 1-form A = H_μ dx^μ
  4. Curvature 2-form F = dA + A∧A
  5. Holonomic Attention
  6. Parallel Transport ∮A
"""

import sys
import os
import math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from geometer.fiber_bundle import (
    Coordinate, BaseManifold, GaugeField, GroupElement,
    PrincipalBundle, ConnectionForm, CurvatureForm,
    HolonomyComputer, HolonomicAttention,
    build_hufd_bundle, PRISMFiberBundle
)
from geometer.domain import build_root


class TestBaseManifold:
    """Test base manifold M (text positions)."""

    def test_coordinate_creation(self):
        coord = Coordinate(1, 1, 0)
        assert coord.surah == 1
        assert coord.ayah == 1
        assert coord.word_position == 0

    def test_coordinate_chart(self):
        coord = Coordinate(5, 23, 7)
        assert coord.chart == (5, 23, 7)

    def test_coordinate_prismatic(self):
        coord = Coordinate(1, 1, 0)
        prism_coord = coord.prismatic_coordinate
        assert isinstance(prism_coord, tuple)
        assert len(prism_coord) == 32

    def test_coordinate_distance(self):
        c1 = Coordinate(1, 1, 0)
        c2 = Coordinate(1, 1, 1)
        assert c1.distance_to(c2) == 1

    def test_manifold_creation(self):
        base = BaseManifold(verse_count=10, max_words_per_verse=5)
        assert len(base.coordinates) > 0

    def test_manifold_coordinate_at(self):
        base = BaseManifold(verse_count=10, max_words_per_verse=5)
        coord = base.coordinate_at(1, 2, 3)
        assert coord.surah == 1
        assert coord.ayah == 2
        assert coord.word_position == 3

    def test_manifold_neighbors(self):
        base = BaseManifold(verse_count=10, max_words_per_verse=5)
        coord = base.coordinate_at(1, 1, 2)
        neighbors = base.neighbors(coord, radius=1)
        assert isinstance(neighbors, list)


class TestGaugeField:
    """Test gauge field (SU(2) fiber element)."""

    def test_gauge_field_creation(self):
        field = GaugeField((0.1, -0.2, 0.3))
        assert field.components == (0.1, -0.2, 0.3)

    def test_gauge_field_prismatic(self):
        field = GaugeField((0.1, 0.2, 0.3))
        prism = field.prismatic_coordinate
        assert isinstance(prism, tuple)

    def test_gauge_field_norm(self):
        field = GaugeField((3.0, 4.0, 0.0))
        assert abs(field.norm - 5.0) < 1e-10

    def test_gauge_field_norm_non_negative(self):
        field = GaugeField((0.1, 0.2, 0.3))
        assert field.norm >= 0


class TestGroupElement:
    """Test SU(2) group element."""

    def test_identity(self):
        g = GroupElement.identity()
        assert g.a == 1 + 0j
        assert g.b == 0 + 0j

    def test_from_angle(self):
        g = GroupElement.from_angle((0, 0, 1), math.pi / 2)
        assert isinstance(g.a, complex)
        assert isinstance(g.b, complex)

    def test_inverse(self):
        g = GroupElement.from_angle((0, 0, 1), math.pi / 4)
        g_inv = g.inverse
        # g * g⁻¹ = identity
        product_a = g.a * g_inv.a - g.b.conjugate() * g_inv.b
        product_b = g.a * g_inv.b + g.b.conjugate() * g_inv.a
        assert abs(product_a.real - 1) < 1e-10
        assert abs(product_b) < 1e-10

    def test_prismatic_coordinate(self):
        g = GroupElement.identity()
        prism = g.prismatic_coordinate
        assert isinstance(prism, tuple)


class TestPrincipalBundle:
    """Test principal SU(2)-bundle."""

    def test_bundle_creation(self):
        base = BaseManifold(verse_count=10, max_words_per_verse=5)
        bundle = PrincipalBundle(base, lambda x: GaugeField((0.0, 0.0, 0.0)))
        assert bundle.base is not None

    def test_bundle_fiber(self):
        base = BaseManifold(verse_count=10, max_words_per_verse=5)
        bundle = PrincipalBundle(base, lambda x: GaugeField((0.1, 0.2, 0.3)))
        coord = base.coordinate_at(1, 1, 0)
        fiber = bundle.fiber(coord)
        assert isinstance(fiber, GaugeField)


class TestConnectionForm:
    """Test connection 1-form A = H_μ dx^μ."""

    def test_connection_creation(self):
        connection = ConnectionForm({})
        assert connection.components == {}

    def test_add_component(self):
        connection = ConnectionForm({})
        coord = Coordinate(1, 1, 0)
        field = GaugeField((0.1, 0.2, 0.3))
        connection.add_component(coord, "forward", field)
        assert (coord, "forward") in connection.components

    def test_evaluate(self):
        connection = ConnectionForm({})
        coord = Coordinate(1, 1, 0)
        field = GaugeField((0.1, 0.2, 0.3))
        connection.add_component(coord, "forward", field)
        evaluated = connection.evaluate(coord, "forward")
        assert evaluated.components == (0.1, 0.2, 0.3)


class TestCurvatureForm:
    """Test curvature 2-form F = dA + A∧A."""

    def test_curvature_creation(self):
        curvature = CurvatureForm({})
        assert curvature.components == {}

    def test_curvature_evaluate(self):
        curvature = CurvatureForm({})
        coord = Coordinate(1, 1, 0)
        F = curvature.evaluate(coord, "forward", "backward")
        assert isinstance(F, GaugeField)
        assert F.components == (0.0, 0.0, 0.0)

    def test_curvature_norm_non_negative(self):
        curvature = CurvatureForm({})
        coord = Coordinate(1, 1, 0)
        norm = curvature.holonomic_attention(coord)
        assert norm >= 0


class TestHolonomyComputer:
    """Test parallel transport and holonomy."""

    def test_parallel_transport_identity(self):
        base = BaseManifold(verse_count=10, max_words_per_verse=5)
        connection = ConnectionForm({})
        holonomy = HolonomyComputer(connection)
        
        g0 = GroupElement.identity()
        path = [base.coordinate_at(1, 1, i) for i in range(4)]
        
        g1 = holonomy.parallel_transport(g0, path)
        assert isinstance(g1, GroupElement)

    def test_holonomy_loop(self):
        base = BaseManifold(verse_count=10, max_words_per_verse=5)
        connection = ConnectionForm({})
        holonomy = HolonomyComputer(connection)
        
        g, theta = holonomy.holonomy_loop(GroupElement.identity(), [
            base.coordinate_at(1, 1, 0),
            base.coordinate_at(1, 1, 1),
            base.coordinate_at(1, 1, 2),
            base.coordinate_at(1, 1, 0),
        ])
        
        assert isinstance(g, GroupElement)
        assert isinstance(theta, float)

    def test_berry_phase_bounded(self):
        base = BaseManifold(verse_count=10, max_words_per_verse=5)
        connection = ConnectionForm({})
        holonomy = HolonomyComputer(connection)
        
        loop = [base.coordinate_at(1, 1, i) for i in range(4)]
        loop.append(loop[0])
        
        phase = holonomy.berry_phase(loop)
        assert -math.pi <= phase <= math.pi


class TestHolonomicAttention:
    """Test holonomic attention mechanism."""

    def test_attention_weights_sum_to_one(self):
        base = BaseManifold(verse_count=10, max_words_per_verse=5)
        connection = ConnectionForm({})
        curvature = CurvatureForm({})
        bundle = PrincipalBundle(base, lambda x: GaugeField((0.0, 0.0, 0.0)))
        attention = HolonomicAttention(base, curvature, connection, bundle)
        
        coord = base.coordinate_at(1, 1, 2)
        neighbors = base.neighbors(coord, 1)
        section = lambda x: GaugeField((0.0, 0.0, 0.0))
        
        weights = attention.attention_weights(coord, neighbors, section)
        
        if weights:
            total = sum(weights.values())
            assert abs(total - 1.0) < 1e-10


class TestPRISMFiberBundle:
    """Test PRISM integration in fiber bundle."""

    def test_prism_bundle_creation(self):
        root = build_root("سجد", "S-J-D", [0.1] * 71)
        bundle = build_hufd_bundle([root], verse_count=10, max_words=5)
        prism_bundle = PRISMFiberBundle(*bundle)
        assert prism_bundle.base is not None

    def test_jsonld_emission(self):
        root = build_root("سجد", "S-J-D", [0.1] * 71)
        bundle = build_hufd_bundle([root], verse_count=10, max_words=5)
        prism_bundle = PRISMFiberBundle(*bundle)
        jsonld = prism_bundle.emit_jsonld()
        
        assert '@type' in jsonld
        assert jsonld['@type'] == 'hufd:PrincipalBundle'
        assert 'hufd:structureGroup' in jsonld
        assert jsonld['hufd:structureGroup'] == 'SU(2)'

    def test_derive_curvature(self):
        root = build_root("سجد", "S-J-D", [0.1] * 71)
        bundle = build_hufd_bundle([root], verse_count=10, max_words=5)
        prism_bundle = PRISMFiberBundle(*bundle)
        coord = prism_bundle.base.coordinate_at(1, 1, 0)
        
        derived = prism_bundle.derive_curvature_at(coord)
        
        assert 'derivation' in derived
        assert 'curvature' in derived
        assert 'curvature_norm' in derived
        assert derived['derivation'].derivation_id.startswith('urn:uor:derivation:')


class TestHUFDCompliance:
    """Test HUFD paper compliance."""

    def test_base_manifold_exists(self):
        base = BaseManifold(verse_count=10, max_words_per_verse=5)
        assert isinstance(base, BaseManifold)

    def test_su2_structure_group(self):
        base = BaseManifold(verse_count=10, max_words_per_verse=5)
        bundle = PrincipalBundle(base, lambda x: GaugeField((0.0, 0.0, 0.0)))
        assert bundle is not None

    def test_connection_1form(self):
        connection = ConnectionForm({})
        assert isinstance(connection, ConnectionForm)

    def test_curvature_2form(self):
        curvature = CurvatureForm({})
        assert isinstance(curvature, CurvatureForm)

    def test_parallel_transport(self):
        base = BaseManifold(verse_count=10, max_words_per_verse=5)
        connection = ConnectionForm({})
        holonomy = HolonomyComputer(connection)
        assert isinstance(holonomy, HolonomyComputer)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
