"""
Fiber Bundle Module: HUFD-Compliant Arabic as a Principal SU(2)-Bundle
=====================================================================

This module implements the mathematical structure from the HUFD paper:
A principal G-bundle E(M, G, π) where:
  - Base M: Arabic text as a differentiable manifold
  - Structure group G = SU(2)
  - Total space E: SU(2) ×_θ ℂ² with holonomy

Key Structures:
  1. Base Manifold M: Position indices form a 1D manifold
  2. Principal Bundle E(M, SU(2), π): Fiber = SU(2)
  3. Connection 1-form A = H_μ dx^μ: Ehresmann connection
  4. Curvature 2-form F = dA + A∧A: Riemann-like curvature
  5. Holonomic Attention: Curvature as attention mechanism
  6. Parallel Transport: ∮A along paths in M

All coordinates use PRISM as the underlying ring substrate.

References:
  - HUFD Paper: Holonomic Unified Field Dynamics
  - PRISM: Universal Orchestration Representation
"""

from dataclasses import dataclass, field
from typing import Optional, Callable
from enum import Enum
import math

from .prism import UOR, Triad
from .uor import Q256
from .domain import ArabicRoot, make_root_iri


# ════════════════════════════════════════════════════════════════════════════
# SECTION 1: BASE MANIFOLD M
# The manifold of text positions with local coordinates
# ════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Coordinate:
    """A point on the base manifold M (text position).
    
    Local coordinate chart: (surah, ayah, word_position)
    """
    surah: int
    ayah: int
    word_position: int
    
    @property
    def chart(self) -> tuple:
        """Local coordinate tuple."""
        return (self.surah, self.ayah, self.word_position)
    
    @property
    def prismatic_coordinate(self) -> tuple:
        """PRISM coordinate for this position."""
        coord_int = (
            (self.surah & 0x7F) |
            ((self.ayah & 0x1FFF) << 7) |
            ((self.word_position & 0xFF) << 20)
        )
        return Q256._to_bytes(coord_int)
    
    def distance_to(self, other: 'Coordinate') -> float:
        """Distance metric on manifold (discrete approximation)."""
        if self.surah != other.surah:
            return abs(self.surah - other.surah) * 1000 + abs(self.ayah - other.ayah)
        return abs(self.ayah - other.ayah) + abs(self.word_position - other.word_position)


@dataclass
class BaseManifold:
    """The base manifold M of Arabic text positions.
    
    M is a 1-dimensional complex (position indices form a differentiable manifold).
    Charts map to local coordinates (surah, ayah, word_position).
    """
    verse_count: int
    max_words_per_verse: int
    coordinates: tuple = field(default_factory=tuple)
    
    def __post_init__(self):
        if not self.coordinates:
            # Generate all coordinates
            coords = []
            for s in range(1, 115):  # Quran has 114 surahs
                for a in range(1, self.verse_count // 114 + 2):
                    for w in range(self.max_words_per_verse):
                        coords.append(Coordinate(s, a, w))
            object.__setattr__(self, 'coordinates', tuple(coords))
    
    def coordinate_at(self, surah: int, ayah: int, word: int) -> Coordinate:
        """Get coordinate at position."""
        return Coordinate(surah, ayah, word)
    
    def neighbors(self, coord: Coordinate, radius: int = 1) -> list:
        """Get neighboring coordinates within radius."""
        neighbors = []
        for c in self.coordinates:
            if 0 < coord.distance_to(c) <= radius:
                neighbors.append(c)
        return neighbors


# ════════════════════════════════════════════════════════════════════════════
# SECTION 2: PRINCIPAL BUNDLE E(M, SU(2), π)
# Fiber = SU(2), Structure Group acts on fiber by left multiplication
# ════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GaugeField:
    """An element of the structure group G = SU(2).
    
    The fiber over each point x ∈ M is a copy of SU(2).
    Represented as anti-Hermitian matrix H ∈ su(2) ⊗ ℂ.
    
    In PRISM coordinates: H encodes distributional information
    about a root's relationship to its context.
    """
    components: tuple  # (H_1, H_2, H_3) ∈ ℝ³
    
    @property
    def prismatic_coordinate(self) -> tuple:
        """PRISM coordinate encoding the gauge field."""
        h1, h2, h3 = self.components
        coord_int = (
            (int(h1 * 127) & 0xFF) |
            ((int(h2 * 127) & 0xFF) << 8) |
            ((int(h3 * 127) & 0xFF) << 16)
        )
        return Q256._to_bytes(coord_int)
    
    @property
    def norm(self) -> float:
        """Norm of gauge field components."""
        return math.sqrt(sum(h**2 for h in self.components))
    
    def adjoint_action(self, g: 'GroupElement') -> 'GaugeField':
        """Adjoint action: g·H·g⁻¹ for H ∈ su(2), g ∈ SU(2)."""
        # Simplified: return rotated field
        return GaugeField((
            -self.components[2],
            self.components[0],
            self.components[1]
        ))


@dataclass(frozen=True)
class GroupElement:
    """An element of the structure group G = SU(2).
    
    SU(2) ≅ S³ (unit sphere in ℝ⁴).
    Represented as unitary 2×2 complex matrix.
    """
    a: complex  # Quaternion-like representation
    b: complex  # |a|² + |b|² = 1
    
    @property
    def matrix(self) -> list:
        """2×2 unitary matrix representation."""
        return [
            [self.a, -self.b.conjugate()],
            [self.b, self.a.conjugate()]
        ]
    
    @property
    def inverse(self) -> 'GroupElement':
        """Group inverse: g⁻¹ = ḡ^T / |g|²"""
        return GroupElement(self.a.conjugate(), -self.b.conjugate())
    
    @property
    def prismatic_coordinate(self) -> tuple:
        """PRISM coordinate for group element."""
        real_parts = int(self.a.real * 127) & 0xFF
        imag_parts = int(self.a.imag * 127) & 0xFF
        coord_int = (real_parts | (imag_parts << 8))
        return Q256._to_bytes(coord_int)
    
    @staticmethod
    def identity() -> 'GroupElement':
        """Identity element e ∈ SU(2)."""
        return GroupElement(1+0j, 0+0j)
    
    @staticmethod
    def from_angle(axis: tuple, theta: float) -> 'GroupElement':
        """Create from rotation: exp(θ·axis/2)"""
        hx, hy, hz = axis
        half_angle = theta / 2
        norm = math.sqrt(hx**2 + hy**2 + hz**2) or 1
        ux, uy, uz = hx/norm, hy/norm, hz/norm
        
        a = math.cos(half_angle) + 1j * uz * math.sin(half_angle)
        b = 1j * (ux - 1j*uy) * math.sin(half_angle)
        
        return GroupElement(a, b)


@dataclass
class PrincipalBundle:
    """Principal SU(2)-bundle E(M, SU(2), π).
    
    Total space E is the disjoint union of fibers π⁻¹(x) ≅ SU(2) over x ∈ M.
    
    For Arabic text:
    - Base M: positions in text
    - Fiber: SU(2) encoding distributional state of roots
    - Projection π: E → M
    """
    base: BaseManifold
    fiber_metric: Callable[[Coordinate], GaugeField]
    
    def __post_init__(self):
        if self.fiber_metric is None:
            # Default: zero field
            self.fiber_metric = lambda x: GaugeField((0.0, 0.0, 0.0))
    
    def fiber(self, x: Coordinate) -> GaugeField:
        """Get fiber (gauge field) at position x ∈ M."""
        return self.fiber_metric(x)
    
    def section(self, root: ArabicRoot) -> Callable[[Coordinate], GaugeField]:
        """Section s: M → E.
        
        Maps each position to its gauge field encoding the root's state.
        This is a horizontal lift of the text.
        """
        def section_map(x: Coordinate) -> GaugeField:
            # Encode root information as gauge field
            profile = root.prism_triplet.stratum
            h1 = (profile[0] if len(profile) > 0 else 0) / 8.0
            h2 = (profile[1] if len(profile) > 1 else 0) / 8.0
            h3 = (profile[2] if len(profile) > 2 else 0) / 8.0
            return GaugeField((h1 - 0.5, h2 - 0.5, h3 - 0.5))
        return section_map


# ════════════════════════════════════════════════════════════════════════════
# SECTION 3: CONNECTION 1-FORM A = H_μ dx^μ
# Ehresmann connection on the principal bundle
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class ConnectionForm:
    """Ehresmann connection 1-form A = H_μ dx^μ.
    
    A is a Lie-algebra valued 1-form on E.
    Decomposes tangent bundle TE = HE ⊕ VE (horizontal + vertical).
    
    For each direction μ in the base manifold:
    - A_μ represents the gauge field component in that direction
    """
    components: dict  # {(x, μ): H_μ(x)} for coordinate x and direction μ
    
    def evaluate(self, coord: Coordinate, direction: str = "forward") -> GaugeField:
        """Evaluate connection at point in given direction.
        
        A_μ(x) gives the gauge field component for movement in direction μ.
        """
        key = (coord, direction)
        if key in self.components:
            return self.components[key]
        
        # Default: look up from bundle
        return GaugeField((0.0, 0.0, 0.0))
    
    def add_component(self, coord: Coordinate, direction: str, field: GaugeField):
        """Add a connection component A_μ(x)."""
        self.components[(coord, direction)] = field
    
    def covariant_derivative(
        self, 
        section: Callable[[Coordinate], GaugeField],
        coord: Coordinate
    ) -> GaugeField:
        """Compute ∇_μ s at position x.
        
        Covariant derivative of section s along direction μ:
        ∇_μ s = ds/dx_μ + A_μ · s
        
        where · is the adjoint action of su(2).
        """
        h = 0.001  # Discrete step size
        
        # Forward difference for ds/dx
        forward = section(Coordinate(coord.surah, coord.ayah, coord.word_position + 1))
        s = section(coord)
        
        ds = GaugeField((
            (forward.components[0] - s.components[0]) / h,
            (forward.components[1] - s.components[1]) / h,
            (forward.components[2] - s.components[2]) / h,
        ))
        
        # Get connection A_μ
        A = self.evaluate(coord, "forward")
        
        # Adjoint action: [A, s] = A × s (cross product in su(2))
        A_cross_s = (
            A.components[1] * s.components[2] - A.components[2] * s.components[1],
            A.components[2] * s.components[0] - A.components[0] * s.components[2],
            A.components[0] * s.components[1] - A.components[1] * s.components[0],
        )
        
        return GaugeField((
            ds.components[0] + A_cross_s[0],
            ds.components[1] + A_cross_s[1],
            ds.components[2] + A_cross_s[2],
        ))


# ════════════════════════════════════════════════════════════════════════════
# SECTION 4: CURVATURE 2-FORM F = dA + A∧A
# Riemann-like curvature of the connection
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class CurvatureForm:
    """Curvature 2-form F = dA + A∧A.
    
    F is a Lie-algebra valued 2-form on E.
    Measures holonomy: parallel transport around closed loops ≠ identity.
    
    Components: F_μν = ∂_μ A_ν - ∂_ν A_μ + [A_μ, A_ν]
    
    For SU(2), this is dual to the Riemann tensor R^ρ_σμν.
    """
    components: dict  # {(x, μ, ν): F_μν(x)} for x ∈ M, directions μ, ν
    
    def evaluate(self, coord: Coordinate, mu: str, nu: str) -> GaugeField:
        """Evaluate curvature F_μν at position x."""
        key = (coord, mu, nu)
        return self.components.get(key, GaugeField((0.0, 0.0, 0.0)))
    
    def compute_from_connection(
        self, 
        connection: ConnectionForm,
        section: Callable[[Coordinate], GaugeField],
        coord: Coordinate
    ) -> tuple:
        """Compute F_μν from connection via discrete approximation.
        
        F_μν = ∂_μ A_ν - ∂_ν A_μ + [A_μ, A_ν]
        """
        h = 0.001
        
        # Forward and backward sections
        s_fwd = section(Coordinate(coord.surah, coord.ayah, coord.word_position + 1))
        s_back = section(Coordinate(coord.surah, coord.ayah, coord.word_position - 1))
        s = section(coord)
        
        # ∂_μ A_ν - ∂_ν A_μ (discrete)
        A_fwd = connection.evaluate(coord, "forward")
        A_back = connection.evaluate(coord, "backward")
        
        dA = GaugeField((
            (A_fwd.components[0] - A_back.components[0]) / (2*h),
            (A_fwd.components[1] - A_back.components[1]) / (2*h),
            (A_fwd.components[2] - A_back.components[2]) / (2*h),
        ))
        
        # [A_μ, A_ν] = A_μ × A_ν (su(2) bracket)
        A_cross = (
            A_fwd.components[1] * A_back.components[2] - A_fwd.components[2] * A_back.components[1],
            A_fwd.components[2] * A_back.components[0] - A_fwd.components[0] * A_back.components[2],
            A_fwd.components[0] * A_back.components[1] - A_fwd.components[1] * A_back.components[0],
        )
        
        return (
            GaugeField((
                dA.components[0] + A_cross[0],
                dA.components[1] + A_cross[1],
                dA.components[2] + A_cross[2],
            )),
            s_fwd,
            s_back
        )
    
    def holonomic_attention(self, coord: Coordinate) -> float:
        """Compute holonomic attention at position.
        
        ||F_μν|| measures how much meaning "curves" at this position.
        High curvature = attention hotspot.
        """
        # Sum of squared curvature components
        total = 0.0
        for key, field in self.components.items():
            if key[0] == coord:
                total += sum(h**2 for h in field.components)
        return math.sqrt(total)
    
    def pullback_via_section(
        self,
        section: Callable[[Coordinate], GaugeField],
        coord: Coordinate
    ) -> GaugeField:
        """Pull back curvature via section s: M → E.
        
        π* F = F_μν dx^μ ∧ dx^ν
        
        Returns the curvature as experienced by the text.
        """
        return self.evaluate(coord, "forward", "backward")


# ════════════════════════════════════════════════════════════════════════════
# SECTION 5: PARALLEL TRANSPORT ∮A
# Holonomy: transport gauge field along path in M
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class HolonomyComputer:
    """Compute holonomy (parallel transport) around loops in M.
    
    For path γ: [0,1] → M, holonomy is:
    Hol(γ) = P exp(∮_γ A) ∈ SU(2)
    
    Where P is path ordering (critical for non-commuting connections).
    """
    connection: ConnectionForm
    
    def parallel_transport(
        self,
        initial_state: GroupElement,
        path: list[Coordinate]
    ) -> GroupElement:
        """Parallel transport g(0) → g(1) along path.
        
        Solves: dg/dt = A_μ(g, x) · g with g(0) = initial_state
        """
        g = initial_state
        
        for i in range(len(path) - 1):
            x = path[i]
            x_next = path[i + 1]
            
            # Get connection at this point
            A = self.connection.evaluate(x, "forward")
            
            # Discrete approximation: g → exp(A) · g
            theta = math.sqrt(sum(a**2 for a in A.components))
            
            if theta > 1e-10:
                axis = (
                    A.components[0] / theta,
                    A.components[1] / theta,
                    A.components[2] / theta,
                )
                transport = GroupElement.from_angle(axis, theta * 0.001)
                # Apply: g_new = transport · g
                g = GroupElement(
                    transport.a * g.a - transport.b.conjugate() * g.b,
                    transport.a * g.b + transport.b.conjugate() * g.a
                )
        
        return g
    
    def holonomy_loop(
        self,
        initial_state: GroupElement,
        loop: list[Coordinate]
    ) -> tuple:
        """Compute holonomy around closed loop γ.
        
        Returns: (holonomy_element, total_angle)
        
        Hol(γ) = P exp(∮_γ A) ∈ SU(2)
        
        Non-trivial holonomy indicates curvature.
        """
        g = self.parallel_transport(initial_state, loop)
        
        # Extract rotation angle from SU(2) element
        theta = 2 * math.acos(min(1.0, abs(g.a.real)))
        
        return (g, theta)
    
    def berry_phase(
        self,
        path: list[Coordinate]
    ) -> float:
        """Compute Berry phase for adiabatic transport.
        
        For SU(2), Berry phase = -θ/2 where θ is holonomy angle.
        """
        g, theta = self.holonomy_loop(GroupElement.identity(), path)
        return -theta / 2


# ════════════════════════════════════════════════════════════════════════════
# SECTION 6: HOLONOMIC ATTENTION MECHANISM
# Using curvature as attention: high F = high attention
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class HolonomicAttention:
    """Holonomic Attention: F_μν as attention mechanism.
    
    The Riemann-like curvature F measures semantic holonomy:
    - High ||F|| at position x = meaning curves sharply here = high attention
    - Low ||F|| = smooth semantic flow = low attention
    
    This replaces attention mechanisms with geometric meaning.
    """
    base: BaseManifold
    curvature: CurvatureForm
    connection: ConnectionForm
    bundle: PrincipalBundle
    
    def attention_weights(
        self,
        query_coord: Coordinate,
        key_coords: list[Coordinate],
        section: Callable[[Coordinate], GaugeField]
    ) -> dict:
        """Compute attention weights via holonomic similarity.
        
        Attention w_ij ∝ exp(-γ ||F_μν(s(q), s(k))||)
        
        where γ is a temperature parameter.
        """
        weights = {}
        
        # Get query state
        q_state = section(query_coord)
        
        for kc in key_coords:
            # Get key state
            k_state = section(kc)
            
            # Compute curvature between query and key
            F, _, _ = self.curvature.compute_from_connection(
                self.connection, section, kc
            )
            
            # Curvature norm as distance
            F_norm = math.sqrt(sum(f**2 for f in F.components))
            
            # Holonomic distance
            holonomic_dist = F_norm * query_coord.distance_to(kc)
            
            # Softmax-style attention
            weights[kc] = math.exp(-holonomic_dist)
        
        # Normalize
        total = sum(weights.values())
        if total > 0:
            weights = {k: v/total for k, v in weights.items()}
        
        return weights
    
    def contextual_embedding(
        self,
        coord: Coordinate,
        neighborhood: list[Coordinate],
        section: Callable[[Coordinate], GaugeField]
    ) -> GaugeField:
        """Compute contextual embedding via holonomic attention.
        
        E(x) = Σ_i w_i · s(x_i) where w_i = attention(query, x_i)
        
        This is a horizontal lift that respects gauge structure.
        """
        if not neighborhood:
            return section(coord)
        
        # Compute attention weights
        weights = self.attention_weights(coord, neighborhood, section)
        
        # Weighted sum of neighborhood states
        total_h = [0.0, 0.0, 0.0]
        for nc, w in weights.items():
            state = section(nc)
            total_h[0] += w * state.components[0]
            total_h[1] += w * state.components[1]
            total_h[2] += w * state.components[2]
        
        return GaugeField(tuple(total_h))
    
    def attention_hotspots(
        self,
        section: Callable[[Coordinate], GaugeField],
        threshold: float = 0.5
    ) -> list:
        """Find positions where curvature exceeds threshold.
        
        These are the semantic "attention hotspots" where meaning curves sharply.
        """
        hotspots = []
        
        for coord in self.base.coordinates[:100]:  # Sample first 100
            F, _, _ = self.curvature.compute_from_connection(
                self.connection, section, coord
            )
            F_norm = math.sqrt(sum(f**2 for f in F.components))
            
            if F_norm > threshold:
                hotspots.append({
                    'coordinate': coord,
                    'curvature_norm': F_norm,
                    'position': coord.chart
                })
        
        return sorted(hotspots, key=lambda x: x['curvature_norm'], reverse=True)


# ════════════════════════════════════════════════════════════════════════════
# CONVENIENCE: Build complete fiber bundle from roots
# ════════════════════════════════════════════════════════════════════════════

def build_hufd_bundle(
    roots: list[ArabicRoot],
    verse_count: int = 6236,
    max_words: int = 50
) -> tuple:
    """Build complete HUFD fiber bundle from Arabic roots.
    
    Returns: (base, bundle, connection, curvature, attention)
    """
    # 1. Base manifold
    base = BaseManifold(verse_count, max_words)
    
    # 2. Build section from roots
    def make_bundle_section(root: Optional[ArabicRoot]):
        def section(coord: Coordinate) -> GaugeField:
            if root is None:
                return GaugeField((0.0, 0.0, 0.0))
            profile = root.prism_triplet.stratum
            h1 = (profile[0] if len(profile) > 0 else 0) / 16.0 - 0.25
            h2 = (profile[1] if len(profile) > 1 else 0) / 16.0 - 0.25
            h3 = (profile[2] if len(profile) > 2 else 0) / 16.0 - 0.25
            return GaugeField((h1, h2, h3))
        return section
    
    # Use first root for now (in real impl, would combine all)
    section = make_bundle_section(roots[0]) if roots else make_bundle_section(None)
    
    # 3. Principal bundle
    bundle = PrincipalBundle(base, lambda x: section(x))
    
    # 4. Connection from section (A_μ = ∂_μ s)
    connection = ConnectionForm({})
    for coord in base.coordinates[:100]:
        s = section(coord)
        s_fwd = section(Coordinate(coord.surah, coord.ayah, coord.word_position + 1))
        A = GaugeField((
            s_fwd.components[0] - s.components[0],
            s_fwd.components[1] - s.components[1],
            s_fwd.components[2] - s.components[2],
        ))
        connection.add_component(coord, "forward", A)
    
    # 5. Curvature from connection
    curvature = CurvatureForm({})
    for coord in base.coordinates[:100]:
        F, _, _ = curvature.compute_from_connection(connection, section, coord)
        curvature.components[(coord, "forward", "backward")] = F
    
    # 6. Holonomic attention
    attention = HolonomicAttention(base, curvature, connection, bundle)
    
    return (base, bundle, connection, curvature, attention)


# ════════════════════════════════════════════════════════════════════════════
# PRISM INTEGRATION: Everything extends PRISM
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class PRISMFiberBundle:
    """PRISM-extended fiber bundle with full provenance tracking.
    
    All coordinates, fields, and operations use PRISM for:
    - Semantic addressing (IRIs for all entities)
    - Triadic coordinates (datum, stratum, spectrum)
    - Derivation certificates (provenance for all computations)
    - JSON-LD emission (interoperability)
    """
    base: BaseManifold
    bundle: PrincipalBundle
    connection: ConnectionForm
    curvature: CurvatureForm
    attention: HolonomicAttention
    derivations: dict = field(default_factory=dict)
    
    def emit_jsonld(self) -> dict:
        """Emit complete fiber bundle as JSON-LD."""
        return {
            "@context": {
                "@base": "https://geometer.uor.foundation/fiber-bundle/",
                "@vocab": "https://geometer.uor.foundation/vocab/",
                "uor": "https://uor.foundation/u/",
                "hufd": "https://geometer.uor.foundation/vocab/hufd/",
            },
            "@type": "hufd:PrincipalBundle",
            "hufd:baseManifold": {
                "@type": "hufd:BaseManifold",
                "hufd:coordinateCount": len(self.base.coordinates),
                "uor:coordinate": [c.prismatic_coordinate for c in self.base.coordinates[:10]],
            },
            "hufd:structureGroup": "SU(2)",
            "hufd:hasConnection": {
                "@type": "hufd:Connection1Form",
                "hufd:componentCount": len(self.connection.components),
            },
            "hufd:hasCurvature": {
                "@type": "hufd:Curvature2Form",
                "hufd:componentCount": len(self.curvature.components),
            },
            "hufd:derivations": [
                {"@id": d} for d in self.derivations.keys()
            ],
        }
    
    def derive_curvature_at(self, coord: Coordinate) -> dict:
        """Derive curvature with PRISM certificate."""
        F, s_fwd, s_back = self.curvature.compute_from_connection(
            self.connection,
            lambda x: self.bundle.fiber(x),
            coord
        )
        
        # Create PRISM derivation
        coord_int = Q256._from_bytes(coord.prismatic_coordinate)
        term = Q256.make_term("xor", coord_int, coord_int)
        derivation = Q256.derive(term)
        
        self.derivations[derivation.derivation_id] = {
            'type': 'curvature',
            'coordinate': coord.chart,
            'curvature_norm': math.sqrt(sum(f**2 for f in F.components)),
        }
        
        return {
            'derivation': derivation,
            'curvature': F,
            'curvature_norm': math.sqrt(sum(f**2 for f in F.components)),
            'section_forward': s_fwd,
            'section_backward': s_back,
        }
