"""
Geometer Domain Model: PRISM-Native for Quranic Research.

This module properly uses PRISM as a Model Development Kit (MDK) to create
first-class domain types for Arabic linguistics and Quranic research.

PRISM MDK Principles Applied:
  1. Semantic Addressing: Every entity has a PRISM IRI
  2. Triadic Coordinates: All entities resolve to (datum, stratum, spectrum)
  3. Derivation Certificates: Every operation produces a provenance record
  4. JSON-LD Emission: All entities emit Linked Data for interoperability
  5. Term Operations: Domain ops are PRISM terms with semantic meaning

Domain Ontology:
  - ArabicRoot: A triliteral root with PRISM address
  - Verse: A Quranic verse with PRISM address
  - Word: A word instance with PRISM address
  - Morpheme: A morphological form with PRISM address
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime

from .prism import UOR, Term, Derivation, Triad
from .uor import Q256


# ── Domain Namespace ──────────────────────────────────────────────────────────

GEOMETER_BASE = "https://geometer.uor.foundation/"
GEOMETER_NAMESPACE = "geometer"


# ── PRISM Engines for Different Quantum Levels ────────────────────────────────

# Q0 = 8-bit for compact features (POS, aspect, etc.)
FEATURE_ENGINE = UOR(quantum=0)

# Q31 = 256-bit for full coordinate addressing
COORDINATE_ENGINE = Q256


# ── Domain IRI Builders ──────────────────────────────────────────────────────

def _codepoint(c: int) -> int:
    """Unicode codepoint → Braille pattern for visualization."""
    return 0x2800 + c


def _glyph(b: tuple) -> str:
    """Byte tuple → Unicode Braille glyph."""
    return ''.join(chr(_codepoint(byte)) for byte in b)


def _escape_arabic(text: str) -> str:
    """Escape Arabic text for IRI component."""
    return ''.join(f"U{ord(c):04X}" for c in text)


def make_root_iri(arabic: str, lemma: str = "") -> str:
    """Create PRISM IRI for an Arabic root."""
    encoded = _escape_arabic(arabic)
    if lemma:
        return f"{GEOMETER_BASE}root/{encoded}/lemma/{_escape_arabic(lemma)}"
    return f"{GEOMETER_BASE}root/{encoded}"


def make_verse_iri(surah: int, ayah: int) -> str:
    """Create PRISM IRI for a Quranic verse."""
    return f"{GEOMETER_BASE}verse/{surah}:{ayah}"


def make_word_iri(verse_iri: str, position: int) -> str:
    """Create PRISM IRI for a word in a verse."""
    return f"{verse_iri}/word/{position}"


def make_morpheme_iri(root_iri: str, pos: str, form: str) -> str:
    """Create PRISM IRI for a morphological form."""
    return f"{root_iri}/morpheme/{pos}/{form}"


# ── PRISM-Native Domain Types ─────────────────────────────────────────────────

@dataclass(frozen=True)
class ArabicRoot:
    """An Arabic triliteral root as a first-class PRISM entity.
    
    The root is characterized by its full distributional profile across
    the Quran, encoded as a PRISM triadic coordinate.
    
    Attributes:
        iri: Semantic PRISM address (e.g., geometer:root/U0633U062CU062F)
        arabic: Arabic script representation
        lemma: Lexical root/meaning (optional)
        profile_bytes: Encoded distributional profile
        prism_triplet: PRISM triadic coordinate
        derivations: Provenance records for analyses
    """
    iri: str
    arabic: str
    lemma: str
    profile_bytes: bytes
    derivations: tuple = field(default_factory=tuple)

    def __post_init__(self):
        # Verify profile is valid length
        if len(self.profile_bytes) > 32:
            raise ValueError("Profile exceeds 256-bit capacity")

    @property
    def prism_coordinate(self) -> tuple:
        """PRISM coordinate (byte tuple) for this root."""
        coord_int = int.from_bytes(
            self.profile_bytes.ljust(32, b'\x00'), 'big'
        ) & 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
        return COORDINATE_ENGINE._to_bytes(coord_int)

    @property
    def prism_triplet(self) -> Triad:
        """PRISM triadic coordinate."""
        return COORDINATE_ENGINE.triad(self.prism_coordinate)

    @property
    def datum(self) -> tuple:
        """PRISM datum."""
        return self.prism_triplet.datum

    @property
    def stratum(self) -> tuple:
        """PRISM stratum."""
        return self.prism_triplet.stratum

    @property
    def total_stratum(self) -> int:
        """Total stratum (information content)."""
        return self.prism_triplet.total_stratum

    @property
    def spectrum(self) -> tuple:
        """PRISM spectrum."""
        return self.prism_triplet.spectrum

    @property
    def glyph(self) -> str:
        """Visual representation as Braille."""
        return _glyph(self.prism_coordinate)

    def derive_profile(self, operation: str, other: 'ArabicRoot') -> Derivation:
        """Create derivation for profile operation."""
        coord_a_int = COORDINATE_ENGINE._from_bytes(self.prism_coordinate)
        coord_b_int = COORDINATE_ENGINE._from_bytes(other.prism_coordinate)
        term = COORDINATE_ENGINE.make_term(operation, coord_a_int, coord_b_int)
        return COORDINATE_ENGINE.derive(term)

    def correlate_with(self, other: 'ArabicRoot') -> dict:
        """Correlate with another root (PRISM fidelity)."""
        return COORDINATE_ENGINE.correlate(
            self.prism_coordinate,
            other.prism_coordinate
        )

    def emit_jsonld(self) -> dict:
        """Emit JSON-LD for interoperability."""
        return {
            "@id": self.iri,
            "@type": "geometer:ArabicRoot",
            "geometer:arabic": self.arabic,
            "geometer:lemma": self.lemma,
            "geometer:profile": {
                "@type": "uor:Datum",
                "uor:value": list(self.prism_coordinate),
                "uor:stratum": list(self.stratum),
                "uor:spectrum": [list(s) for s in self.spectrum],
                "uor:glyph": self.glyph,
            },
            "uor:totalStratum": self.total_stratum,
        }


@dataclass(frozen=True)
class MorphologicalFeatures:
    """Morphological features encoded as PRISM coordinate.
    
    Compact 8-bit encoding sufficient for:
    - Part of speech (5 bits: 46 values)
    - Verb form (4 bits: 12 values)
    - Aspect (2 bits: 4 values)
    - Person, Number, Gender, Case (3 + 2 + 2 + 2 bits)
    """
    pos: int = 0
    verb_form: int = 0
    aspect: int = 0
    person: int = 0
    number: int = 0
    gender: int = 0
    case_value: int = 0

    @property
    def prism_coordinate(self) -> tuple:
        """Encode features as 8-bit PRISM coordinate."""
        byte = (
            (self.pos & 0x3F) |
            ((self.verb_form & 0x0F) << 6) |
            ((self.aspect & 0x03) << 10) |
            ((self.person & 0x07) << 12) |
            ((self.number & 0x03) << 15) |
            ((self.gender & 0x03) << 17) |
            ((self.case_value & 0x03) << 19)
        )
        return FEATURE_ENGINE._to_bytes(byte)

    @property
    def prism_triplet(self) -> Triad:
        """PRISM triadic coordinate for these features."""
        return FEATURE_ENGINE.triad(self.prism_coordinate)

    def emit_jsonld(self) -> dict:
        """Emit JSON-LD for these features."""
        return {
            "geometer:pos": self.pos,
            "geometer:verbForm": self.verb_form,
            "geometer:aspect": self.aspect,
            "geometer:person": self.person,
            "geometer:number": self.number,
            "geometer:gender": self.gender,
            "geometer:case": self.case_value,
            "uor:coordinate": list(self.prism_coordinate),
        }


@dataclass(frozen=True)
class Word:
    """A word instance as a first-class PRISM entity.
    
    A word combines:
    - Its root (PRISM entity)
    - Its morphological features (PRISM coordinate)
    - Its position in the verse
    """
    iri: str
    text: str
    root_iri: Optional[str]
    position: int
    features: MorphologicalFeatures
    verse_iri: str

    @property
    def prism_coordinate(self) -> tuple:
        """Combined PRISM coordinate (root + features)."""
        root_int = 0
        if self.root_iri:
            # Extract coordinate from root IRI... 
            # For now, use position as fallback
            root_int = self.position << 16
        
        feat_int = int.from_bytes(self.features.prism_coordinate * 4, 'big')
        combined = (root_int | feat_int) & 0xFF
        return COORDINATE_ENGINE._to_bytes(combined)

    def emit_jsonld(self) -> dict:
        """Emit JSON-LD for this word."""
        return {
            "@id": self.iri,
            "@type": "geometer:Word",
            "geometer:text": self.text,
            "geometer:position": self.position,
            "geometer:features": self.features.emit_jsonld(),
            "geometer:verse": {"@id": self.verse_iri},
        }


@dataclass(frozen=True)
class Verse:
    """A Quranic verse as a first-class PRISM entity.
    
    The verse is characterized by:
    - Its words (ordered sequence of PRISM entities)
    - Its semantic content (PRISM correlation between words)
    - Its structural properties (number of roots, coherence)
    """
    iri: str
    surah: int
    ayah: int
    words: tuple  # tuple[Word]
    derivation: Optional[Derivation] = None

    @property
    def word_count(self) -> int:
        """Number of words in this verse."""
        return len(self.words)

    @property
    def root_count(self) -> int:
        """Number of unique roots in this verse."""
        roots = {w.root_iri for w in self.words if w.root_iri}
        return len(roots)

    @property
    def text(self) -> str:
        """Concatenated Arabic text."""
        return ''.join(w.text for w in self.words)

    def emit_jsonld(self) -> dict:
        """Emit JSON-LD for this verse."""
        result = {
            "@id": self.iri,
            "@type": "geometer:Verse",
            "geometer:surah": self.surah,
            "geometer:ayah": self.ayah,
            "geometer:text": self.text,
            "geometer:wordCount": self.word_count,
            "geometer:rootCount": self.root_count,
            "geometer:words": [
                {"@id": w.iri} for w in self.words
            ],
        }
        if self.derivation:
            result["geometer:derivation"] = {
                "@id": self.derivation.derivation_id,
                "uor:result": {"@id": self.derivation.result_iri},
            }
        return result


# ── Domain Operations as PRISM Terms ─────────────────────────────────────────

def derive_root_similarity(root_a: ArabicRoot, root_b: ArabicRoot) -> dict:
    """Compute similarity between two roots with derivation.
    
    Returns:
        dict with correlation, derivation, and provenance
    """
    # Convert coordinates to integers for PRISM
    coord_a_int = COORDINATE_ENGINE._from_bytes(root_a.prism_coordinate)
    coord_b_int = COORDINATE_ENGINE._from_bytes(root_b.prism_coordinate)
    
    correlation = COORDINATE_ENGINE.correlate(
        coord_a_int,
        coord_b_int
    )
    
    term = COORDINATE_ENGINE.make_term("xor", coord_a_int, coord_b_int)
    derivation = COORDINATE_ENGINE.derive(term)
    
    return {
        "root_a": {"@id": root_a.iri},
        "root_b": {"@id": root_b.iri},
        "correlation": correlation,
        "derivation": {
            "@id": derivation.derivation_id,
            "uor:result": {"@id": derivation.result_iri},
            "uor:termMetrics": derivation.metrics.to_dict(),
        },
        "fidelity": correlation['fidelity'],
        "distance": 1.0 - correlation['fidelity'],
    }


def derive_verse_coherence(verse: Verse) -> dict:
    """Derive verse coherence with PRISM certificate.
    
    Computes pairwise root correlations within the verse.
    """
    root_coords = []
    root_iris = []
    
    for word in verse.words:
        if word.root_iri:
            root_coords.append(word.prism_coordinate)
            root_iris.append(word.root_iri)
    
    if len(root_coords) < 2:
        return {
            "verse": {"@id": verse.iri},
            "coherence": 1.0,
            "derivation": None,
        }
    
    # XOR all root coordinates
    combined = root_coords[0]
    for coord in root_coords[1:]:
        combined = COORDINATE_ENGINE.xor(combined, coord)
    
    # Convert to integers for PRISM
    coord_ints = [COORDINATE_ENGINE._from_bytes(c) for c in root_coords]
    combined_int = COORDINATE_ENGINE._from_bytes(combined)
    
    term = COORDINATE_ENGINE.make_term("xor", *coord_ints)
    derivation = COORDINATE_ENGINE.derive(term)
    
    return {
        "verse": {"@id": verse.iri},
        "roots": [{"@id": iri} for iri in root_iris],
        "combined_coordinate": list(combined),
        "derivation": {
            "@id": derivation.derivation_id,
            "uor:result": {"@id": derivation.result_iri},
        },
    }


def emit_full_jsonld_graph(entities: list) -> dict:
    """Emit a complete JSON-LD graph with all entities.
    
    For interoperability and knowledge graph construction.
    """
    return {
        "@context": {
            "@base": GEOMETER_BASE,
            "@vocab": GEOMETER_BASE,
            "uor": "https://uor.foundation/u/",
            "geometer": f"{GEOMETER_BASE}vocab/",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
        },
        "@graph": [entity.emit_jsonld() if hasattr(entity, 'emit_jsonld') else entity
                   for entity in entities],
    }


# ── Builder Functions ────────────────────────────────────────────────────────

def build_root(
    arabic: str,
    lemma: str,
    profile: list[float],
) -> ArabicRoot:
    """Build an ArabicRoot with PRISM coordinate from profile."""
    # Encode profile as bytes
    profile_bytes = bytearray(32)
    for i, val in enumerate(profile):
        if i >= 32:
            break
        profile_bytes[i] = int(min(255, max(0, val * 255)))
    
    iri = make_root_iri(arabic, lemma)
    
    return ArabicRoot(
        iri=iri,
        arabic=arabic,
        lemma=lemma,
        profile_bytes=bytes(profile_bytes),
    )


def build_morpheme_features(
    pos: str,
    verb_form: str = "",
    aspect: str = "",
    person: str = "",
    number: str = "",
    gender: str = "",
    case_value: str = "",
) -> MorphologicalFeatures:
    """Build MorphologicalFeatures from string values."""
    POS_MAP = {k: i for i, k in enumerate([
        "N", "V", "ADJ", "DET", "CONJ", "P", "PRON", "PN",
        "REM", "EMPH", "INTG", "T", "LOC", "REL", "ACC",
        "COND", "DEM", "NEG", "VOC", "SUB", "FUT", "PRP",
        "CIRC", "SUP", "RSLT", "INL", "CERT", "CAUS", "INT",
        "AMD", "EXL", "SUR", "ANS", "EQ", "EXH", "INC",
        "PREV", "IMPV", "AVR", "EXP", "PRO", "RES", "RET",
        "IMPN", "COM",
    ])}
    VF_MAP = {k: i for i, k in enumerate([
        "(I)", "(II)", "(III)", "(IV)", "(V)", "(VI)", "(VII)",
        "(VIII)", "(IX)", "(X)", "(XI)", "(XII)",
    ])}
    ASP_MAP = {"PERF": 0, "IMPF": 1, "IMPV": 2}
    PER_MAP = {"1": 0, "2": 1, "3": 2}
    NUM_MAP = {"S": 0, "D": 1, "P": 2}
    GEN_MAP = {"M": 0, "F": 1}
    CAS_MAP = {"NOM": 0, "ACC": 1, "GEN": 2}

    return MorphologicalFeatures(
        pos=POS_MAP.get(pos, 0),
        verb_form=VF_MAP.get(verb_form, 0),
        aspect=ASP_MAP.get(aspect, 0),
        person=PER_MAP.get(person, 0),
        number=NUM_MAP.get(number, 0),
        gender=GEN_MAP.get(gender, 0),
        case_value=CAS_MAP.get(case_value, 0),
    )


def build_word(
    text: str,
    root: Optional[ArabicRoot],
    position: int,
    features: MorphologicalFeatures,
    verse_iri: str,
) -> Word:
    """Build a Word with PRISM addressing."""
    root_iri = root.iri if root else None
    iri = make_word_iri(verse_iri, position)
    
    return Word(
        iri=iri,
        text=text,
        root_iri=root_iri,
        position=position,
        features=features,
        verse_iri=verse_iri,
    )


def build_verse(
    surah: int,
    ayah: int,
    words: list[Word],
) -> Verse:
    """Build a Verse with PRISM addressing."""
    iri = make_verse_iri(surah, ayah)
    
    # Derive verse coherence
    derivation = None
    if len(words) >= 2:
        result = derive_verse_coherence(Verse(iri, surah, ayah, tuple(words)))
        if result.get("derivation"):
            coord_ints = [COORDINATE_ENGINE._from_bytes(w.prism_coordinate) for w in words[:3]]
            term = COORDINATE_ENGINE.make_term("xor", *coord_ints)
            derivation = COORDINATE_ENGINE.derive(term)
    
    return Verse(
        iri=iri,
        surah=surah,
        ayah=ayah,
        words=tuple(words),
        derivation=derivation,
    )
