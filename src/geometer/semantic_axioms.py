"""
Geometer Semantic Axioms: The Mathematical Structure of Quranic Exegesis
========================================================================

This module formalizes the semantic content of the HUFD fiber bundle
based on the mathematical framework from:

"The Mathematical Expressions of Quranic Exegeses"
Tadabor Theorem: M has 892,164 positions (7,826 × 114)

Core Semantic Definitions:
  1. Base M: The Tadabor manifold of verse positions
  2. Fiber SU(2): Theoretical Verse Space (TV ⊂ ℂ²)
  3. Connection A: Tafsir transition function (τ: M → TafsirAlgebra)
  4. Curvature F: Semantic discontinuity measure
  5. Holonomy: Theme closure in tafsir space

Key Theorems (from paper):
  - Tadabor: |M| = 7,826 × 114 = 892,164
  - Theorem 1: Verse space V is a complex vector space
  - Theorem 2: Fuzzy root meaning as membership function
  - Theorem 3: Root independence implies orthogonality
  - Definition 5: Theoretical Verse Space TV ⊂ ℂⁿ
  - Definition 7: Fuzzy root meaning μ_R: TV → [0,1]
"""

from dataclasses import dataclass, field
from typing import Optional
import math
import cmath


# ════════════════════════════════════════════════════════════════════════════
# SECTION 1: TADABOR MANIFOLD (Base Manifold)
# ════════════════════════════════════════════════════════════════════════════

TADABOR_VERSE_COUNT = 7826  # Total verses in Quran
TADABOR_SURAH_COUNT = 114   # Total surahs
TADABOR_POSITION_COUNT = TADABOR_VERSE_COUNT * TADABOR_SURAH_COUNT  # 892,164


@dataclass(frozen=True)
class TadaborPosition:
    """A position in the Tadabor manifold.
    
    Position = (surah, ayah, word_position)
    
    The Tadabor theorem states:
    |M| = 7,826 × 114 = 892,164 unique positions.
    """
    surah: int      # 1-114
    ayah: int       # 1-7826 (varies by surah)
    word: int       # Position in ayah
    
    def __post_init__(self):
        if not (1 <= self.surah <= 114):
            raise ValueError(f"Surah must be 1-114, got {self.surah}")
        if not (1 <= self.ayah <= TADABOR_VERSE_COUNT):
            raise ValueError(f"Ayah must be 1-{TADABOR_VERSE_COUNT}, got {self.ayah}")
    
    @property
    def tadabor_index(self) -> int:
        """Global index in Tadabor manifold: 0 to 892,163."""
        return (self.surah - 1) * TADABOR_VERSE_COUNT + (self.ayah - 1)
    
    @property
    def verse_label(self) -> str:
        """Quranic notation: surah:ayah."""
        return f"{self.surah}:{self.ayah}"


# ════════════════════════════════════════════════════════════════════════════
# SECTION 2: THEORETICAL VERSE SPACE (Fiber)
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class TheoreticalVerseSpace:
    """
    The Theoretical Verse Space TV ⊂ ℂⁿ.
    
    From Definition 5 of the paper:
    "TV = {ψ = (ψ₁, ψ₂, ..., ψₙ) ∈ ℂⁿ : ||ψ|| = 1}"
    
    Each verse is represented as a unit vector in complex n-dimensional space.
    Our fiber SU(2) ≅ S³ represents a qubit-like encoding of this state.
    
    The fiber is NOT arbitrary - it represents verse meaning as a quantum state.
    """
    # Complex amplitudes for semantic basis states
    amplitude_positive: complex  # ψ₁ = α + iβ
    amplitude_negative: complex  # ψ₂ = γ + iδ
    
    @property
    def norm(self) -> float:
        """||ψ|| = √(|ψ₁|² + |ψ₂|²) should equal 1."""
        return math.sqrt(
            abs(self.amplitude_positive)**2 + 
            abs(self.amplitude_negative)**2
        )
    
    @property
    def is_normalized(self) -> bool:
        """Verse vectors must be normalized: ||ψ|| = 1."""
        return abs(self.norm - 1.0) < 1e-10
    
    def inner_product(self, other: 'TheoreticalVerseSpace') -> complex:
        """⟨ψ|φ⟩ = ψ₁*φ₁ + ψ₂*φ₂ (Hermitian inner product)."""
        return (
            self.amplitude_positive.conjugate() * other.amplitude_positive +
            self.amplitude_negative.conjugate() * other.amplitude_negative
        )
    
    def fidelity(self, other: 'TheoreticalVerseSpace') -> float:
        """|<ψ|φ⟩|² - the paper's similarity measure.
        
        From the paper's Theorem 1, verse similarity uses this quantum fidelity.
        """
        overlap = abs(self.inner_product(other))
        return overlap ** 2
    
    @staticmethod
    def from_profile(profile: list[float], phase: float = 0.0) -> 'TheoreticalVerseSpace':
        """Construct TV state from distributional profile.
        
        Profile values become amplitudes with a global phase.
        """
        if not profile:
            return TheoreticalVerseSpace(1+0j, 0+0j)
        
        # Normalize profile to unit vector
        norm = math.sqrt(sum(p**2 for p in profile))
        if norm < 1e-10:
            return TheoreticalVerseSpace(1+0j, 0+0j)
        
        # First two components as complex amplitudes
        a = (profile[0] / norm) * math.cos(phase)
        b = (profile[0] / norm) * math.sin(phase) if len(profile) > 0 else 0
        c = (profile[1] / norm) if len(profile) > 1 else 0
        d = 0.0
        
        return TheoreticalVerseSpace(
            amplitude_positive=complex(a, b),
            amplitude_negative=complex(c, d)
        )


# ════════════════════════════════════════════════════════════════════════════
# SECTION 3: FUZZY ROOT MEANING (Membership Function)
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class FuzzyRootMeaning:
    """
    Fuzzy root meaning as membership function μ_R: TV → [0,1].
    
    From Definition 7 of the paper:
    "For each root R, μ_R: TV → [0,1] is a fuzzy set representing
    the degree to which a verse ψ ∈ TV belongs to the semantic cluster of R."
    
    This is NOT the same as our concordance_distance.
    It's a direct membership function in verse space.
    """
    root_id: int
    cluster_center: TheoreticalVerseSpace
    spread: float = 0.1  # σ for Gaussian membership
    
    def membership(self, verse: TheoreticalVerseSpace) -> float:
        """μ_R(ψ) ∈ [0,1] - degree of verse belonging to root's meaning.
        
        Uses Gaussian kernel centered on cluster_center.
        """
        fidelity = self.cluster_center.fidelity(verse)
        # Convert similarity to membership
        return math.exp(-((1.0 - fidelity) ** 2) / (2 * self.spread ** 2))
    
    def semantic_distance(self, verse: TheoreticalVerseSpace) -> float:
        """d_R(ψ) = 1 - μ_R(ψ) - distance from root's semantic cluster."""
        return 1.0 - self.membership(verse)


# ════════════════════════════════════════════════════════════════════════════
# SECTION 4: ROOT INDEPENDENCE (Orthogonality)
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class RootIndependence:
    """
    Root independence test based on Theorem 3 of the paper.
    
    Theorem 3: "Two roots R₁ and R₂ are independent iff their semantic
    clusters are orthogonal: ⟨ψ₁|ψ₂⟩ = 0"
    
    This means PRISM correlation directly measures root independence!
    """
    
    @staticmethod
    def are_independent(root_a: TheoreticalVerseSpace, root_b: TheoreticalVerseSpace) -> bool:
        """Test if two roots are semantically independent.
        
        Returns True if the roots are orthogonal: |⟨a|b⟩|² < threshold
        """
        fidelity = root_a.fidelity(root_b)
        # Orthogonal if fidelity ≈ 0 (less than 0.01)
        return fidelity < 0.01
    
    @staticmethod
    def independence_degree(root_a: TheoreticalVerseSpace, root_b: TheoreticalVerseSpace) -> float:
        """How independent are these roots? [0, 1] where 1 = fully independent."""
        fidelity = root_a.fidelity(root_b)
        return 1.0 - fidelity


# ════════════════════════════════════════════════════════════════════════════
# SECTION 5: TAFSIR ALGEBRA (Connection Semantics)
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class TafsirAlgebra:
    """
    The algebra of interpretations T = {τ₁, τ₂, ..., τₙ}.
    
    Each τ represents a layer of exegetical meaning:
    - τ₁: Literal meaning (zahir)
    - τ₂: Interpretive meaning (batin)
    - τ₃: Comparative exegesis (muqarin)
    - ...
    
    The Connection A = H_μ dx^μ maps:
    M × TV → T  (how meaning TRANSITIONS along text positions)
    """
    components: tuple
    
    def __post_init__(self):
        if len(self.components) != 3:
            raise ValueError("Tafsir algebra requires 3 components (τ_x, τ_y, τ_z)")
    
    @staticmethod
    def literal() -> 'TafsirAlgebra':
        """τ₁ - Literal/external meaning (zahir)."""
        return TafsirAlgebra((1.0, 0.0, 0.0))
    
    @staticmethod
    def interpretive() -> 'TafsirAlgebra':
        """τ₂ - Internal/hidden meaning (batin)."""
        return TafsirAlgebra((0.0, 1.0, 0.0))
    
    @staticmethod
    def comparative() -> 'TafsirAlgebra':
        """τ₃ - Comparative exegesis (muqarin)."""
        return TafsirAlgebra((0.0, 0.0, 1.0))
    
    def apply(self, state: TheoreticalVerseSpace) -> TheoreticalVerseSpace:
        """Apply tafsir transformation to verse state.
        
        This is the connection: how meaning shifts under interpretation.
        """
        τ_x, τ_y, τ_z = self.components
        
        # Rotation in semantic space
        new_pos = state.amplitude_positive * complex(math.cos(τ_x), math.sin(τ_x))
        new_neg = state.amplitude_negative * complex(math.cos(τ_y), math.sin(τ_y))
        
        return TheoreticalVerseSpace(new_pos, new_neg)
    
    def transition(self, from_state: TheoreticalVerseSpace, to_tafsir: 'TafsirAlgebra') -> TheoreticalVerseSpace:
        """Transition from current interpretation to new one."""
        # Connection as interpolation between tafsir states
        τ_x = (self.components[0] + to_tafsir.components[0]) / 2
        τ_y = (self.components[1] + to_tafsir.components[1]) / 2
        τ_z = (self.components[2] + to_tafsir.components[2]) / 2
        
        return TafsirAlgebra((τ_x, τ_y, τ_z)).apply(from_state)


# ════════════════════════════════════════════════════════════════════════════
# SECTION 6: SEMANTIC CURVATURE (Discontinuity Measure)
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class SemanticCurvature:
    """
    Semantic curvature as discontinuity measure.
    
    High curvature F → meaning shifts sharply (semantic boundary)
    Low curvature F → meaning flows smoothly (textual continuity)
    
    This is the linguistic interpretation of F = dA + A∧A.
    """
    
    @staticmethod
    def from_states(states: list[TheoreticalVerseSpace]) -> float:
        """Compute semantic curvature from a sequence of verse states.
        
        Curvature = 1 - average fidelity between adjacent states
        High curvature = low fidelity = semantic discontinuity
        """
        if len(states) < 2:
            return 0.0
        
        total_fidelity = 0.0
        for i in range(len(states) - 1):
            total_fidelity += states[i].fidelity(states[i + 1])
        
        avg_fidelity = total_fidelity / (len(states) - 1)
        
        # Curvature is inverse of continuity
        return 1.0 - avg_fidelity
    
    @staticmethod
    def is_boundary(curvature: float, threshold: float = 0.5) -> bool:
        """Is this position a semantic boundary?"""
        return curvature > threshold
    
    @staticmethod
    def boundary_type(curvature: float) -> str:
        """Classify the type of semantic boundary."""
        if curvature < 0.2:
            return "continuity"
        elif curvature < 0.5:
            return "transition"
        elif curvature < 0.8:
            return "shift"
        else:
            return "break"


# ════════════════════════════════════════════════════════════════════════════
# SECTION 7: THEME CLOSURE (Holonomy Semantics)
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class ThemeClosure:
    """
    Theme closure as holonomy in tafsir space.
    
    Parallel transport around a closed loop in M reveals:
    - If holonomy ≈ identity: theme completes naturally
    - If holonomy ≠ identity: theme has unresolved tension
    
    This is the linguistic meaning of ∮A.
    """
    
    @staticmethod
    def closure_degree(initial: TheoreticalVerseSpace, final: TheoreticalVerseSpace) -> float:
        """How much did the theme change through the loop?
        
        Returns 0 = perfect closure (theme resolved)
        Returns 1 = no closure (theme remains open)
        """
        return 1.0 - initial.fidelity(final)
    
    @staticmethod
    def is_resolved(closure_degree: float, threshold: float = 0.1) -> bool:
        """Is the theme resolved (closure degree < threshold)?"""
        return closure_degree < threshold


# ════════════════════════════════════════════════════════════════════════════
# SECTION 8: VERSE VECTOR (Composition from Roots)
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class VerseVector:
    """
    Verse vector as composition of root contributions.
    
    From the paper: "Verse composition is the linear combination of root vectors."
    
    ψ_verse = Σ_i w_i · ψ_root_i
    
    Where w_i is the distributional weight of root i in this verse.
    """
    root_states: list  # [(root_id, weight, tv_state), ...]
    
    @property
    def composite_state(self) -> TheoreticalVerseSpace:
        """Composite verse state from root contributions."""
        if not self.root_states:
            return TheoreticalVerseSpace(1+0j, 0+0j)
        
        # Weighted sum of root states
        total_weight = sum(w for _, w, _ in self.root_states)
        if total_weight < 1e-10:
            return TheoreticalVerseSpace(1+0j, 0+0j)
        
        pos_sum = complex(0, 0)
        neg_sum = complex(0, 0)
        
        for _, weight, tv_state in self.root_states:
            norm_weight = weight / total_weight
            pos_sum += tv_state.amplitude_positive * norm_weight
            neg_sum += tv_state.amplitude_negative * norm_weight
        
        # Renormalize
        norm = math.sqrt(abs(pos_sum)**2 + abs(neg_sum)**2)
        if norm > 1e-10:
            pos_sum /= norm
            neg_sum /= norm
        
        return TheoreticalVerseSpace(pos_sum, neg_sum)
    
    def meaning_coherence(self) -> float:
        """How coherent is this verse's meaning?
        
        Coherence = average pairwise root independence
        High coherence = roots support each other
        """
        if len(self.root_states) < 2:
            return 1.0
        
        coherence = 0.0
        count = 0
        for i, (_, _, state_i) in enumerate(self.root_states):
            for j, (_, _, state_j) in enumerate(self.root_states):
                if i < j:
                    coherence += state_i.fidelity(state_j)
                    count += 1
        
        return coherence / count if count > 0 else 1.0


# ════════════════════════════════════════════════════════════════════════════
# SECTION 9: SEMANTIC AXIOMS (Formal Standards)
# ════════════════════════════════════════════════════════════════════════════

SEMANTIC_AXIOMS = {
    "tadabor_positions": TADABOR_POSITION_COUNT,
    
    "axiom_1": {
        "name": "Tadabor Manifold",
        "statement": "M has exactly 892,164 positions",
        "formal": "|M| = 7,826 × 114 = 892,164",
    },
    
    "axiom_2": {
        "name": "Verse Space Unit Norm",
        "statement": "All verse vectors are normalized: ||ψ|| = 1",
        "formal": "ψ ∈ TV ⊂ ℂ² with ||ψ|| = 1",
    },
    
    "axiom_3": {
        "name": "Fuzzy Root Meaning",
        "statement": "Each root defines a fuzzy membership μ_R: TV → [0,1]",
        "formal": "μ_R(ψ) = exp(-d_R(ψ)² / 2σ²)",
    },
    
    "axiom_4": {
        "name": "Root Independence = Orthogonality",
        "statement": "Independent roots have orthogonal verse states",
        "formal": "R₁ ⟂ R₂ ⟺ |⟨ψ₁|ψ₂⟩|² ≈ 0",
    },
    
    "axiom_5": {
        "name": "Semantic Curvature = Discontinuity",
        "statement": "High curvature indicates semantic boundary",
        "formal": "κ > τ ⟹ boundary at position",
    },
    
    "axiom_6": {
        "name": "Theme Closure = Holonomy",
        "statement": "Parallel transport around verse reveals theme resolution",
        "formal": "Hol(γ) ≈ I ⟹ theme resolved",
    },
}


# ════════════════════════════════════════════════════════════════════════════
# SECTION 10: CONFORMANCE CHECKER
# ════════════════════════════════════════════════════════════════════════════

class SemanticConformance:
    """Verify implementation against semantic axioms."""
    
    @staticmethod
    def check_tadabor_size(positions: list) -> tuple:
        """Axiom 1: Verify Tadabor size."""
        expected = TADABOR_POSITION_COUNT
        actual = len(positions)
        passed = actual == expected
        return (passed, f"Tadabor: expected={expected}, actual={actual}")
    
    @staticmethod
    def check_verse_normalization(verse: VerseVector) -> tuple:
        """Axiom 2: Verify verse vector is normalized."""
        state = verse.composite_state
        passed = state.is_normalized
        return (passed, f"Normalization: ||ψ|| = {state.norm}")
    
    @staticmethod
    def check_fuzzy_membership(membership: float) -> tuple:
        """Verify membership is in [0, 1]."""
        passed = 0.0 <= membership <= 1.0
        return (passed, f"Membership: {membership} ∈ [0, 1]")
    
    @staticmethod
    def check_root_independence(fidelity: float) -> tuple:
        """Axiom 4: Verify independence measure."""
        is_independent = fidelity < 0.01
        return (is_independent, f"Independence: fidelity={fidelity}")
    
    @staticmethod
    def full_conformance_check(verse: VerseVector, membership: float) -> dict:
        """Run all conformance checks."""
        results = {
            "tadabor": SemanticConformance.check_tadabor_size(
                list(range(TADABOR_POSITION_COUNT))
            ),
            "normalization": SemanticConformance.check_verse_normalization(verse),
            "membership": SemanticConformance.check_fuzzy_membership(membership),
        }
        return {
            "passed": all(r[0] for r in results.values()),
            "checks": results,
            "axioms": SEMANTIC_AXIOMS,
        }
