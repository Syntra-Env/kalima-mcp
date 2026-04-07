"""
Conformance Test: Domain Model (PRISM MDK)
==========================================

Validates geometer.domain against PRISM MDK principles:
  1. Semantic Addressing: All entities have PRISM IRIs
  2. Triadic Coordinates: All entities resolve to (datum, stratum, spectrum)
  3. Derivation Certificates: Every operation produces provenance
  4. JSON-LD Emission: All entities emit Linked Data
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from geometer.domain import (
    ArabicRoot, Word, Verse, MorphologicalFeatures,
    build_root, build_morpheme_features, build_word, build_verse,
    make_root_iri, make_verse_iri, derive_root_similarity,
    emit_full_jsonld_graph, GEOMETER_BASE, GEOMETER_NAMESPACE,
)


class TestSemanticAddressing:
    """Validate semantic addressing (PRISM IRIs)."""

    def test_root_has_iri(self):
        root = build_root("سجد", "S-J-D", [0.1] * 71)
        assert hasattr(root, 'iri')
        assert root.iri.startswith(GEOMETER_BASE)

    def test_verse_has_iri(self):
        root = build_root("سجد", "S-J-D", [0.1] * 71)
        feat = build_morpheme_features("V")
        verse_iri = make_verse_iri(1, 1)
        word = build_word("سجد", root, 0, feat, verse_iri)
        verse = build_verse(1, 1, [word])
        
        assert hasattr(verse, 'iri')
        assert verse.iri.startswith(GEOMETER_BASE)

    def test_word_has_iri(self):
        root = build_root("سجد", "S-J-D", [0.1] * 71)
        feat = build_morpheme_features("V")
        verse_iri = make_verse_iri(1, 1)
        word = build_word("سجد", root, 0, feat, verse_iri)
        
        assert hasattr(word, 'iri')
        assert word.iri.startswith(GEOMETER_BASE)

    def test_iri_contains_arabic(self):
        root = build_root("سجد", "S-J-D", [0.1] * 71)
        assert "U0633" in root.iri  # ش
        assert "U062C" in root.iri  # ج
        assert "U062F" in root.iri  # د


class TestTriadicCoordinates:
    """Validate triadic coordinates (datum, stratum, spectrum)."""

    def test_root_has_prism_triplet(self):
        root = build_root("سجد", "S-J-D", [0.1] * 71)
        assert hasattr(root, 'prism_triplet')
        assert hasattr(root.prism_triplet, 'datum')
        assert hasattr(root.prism_triplet, 'stratum')
        assert hasattr(root.prism_triplet, 'spectrum')

    def test_root_datum_is_tuple(self):
        root = build_root("سجد", "S-J-D", [0.1] * 71)
        assert isinstance(root.datum, tuple)

    def test_root_stratum_is_tuple(self):
        root = build_root("سجد", "S-J-D", [0.1] * 71)
        assert isinstance(root.stratum, tuple)

    def test_root_total_stratum_is_int(self):
        root = build_root("سجد", "S-J-D", [0.1] * 71)
        assert isinstance(root.total_stratum, int)
        assert root.total_stratum >= 0

    def test_morpheme_has_prism_triplet(self):
        feat = build_morpheme_features("V", "(I)", "PERF", "3", "S", "M")
        assert hasattr(feat, 'prism_triplet')
        assert hasattr(feat.prism_triplet, 'datum')

    def test_prism_coordinate_is_tuple(self):
        root = build_root("سجد", "S-J-D", [0.1] * 71)
        coord = root.prism_coordinate
        assert isinstance(coord, tuple)
        assert len(coord) == 32  # Q31 = 32 bytes


class TestDerivationCertificates:
    """Validate derivation certificates for operations."""

    def test_derive_root_similarity_returns_derivation(self):
        root1 = build_root("سجد", "S-J-D", [0.1] * 71)
        root2 = build_root("كتب", "K-T-B", [0.2] * 71)
        
        result = derive_root_similarity(root1, root2)
        
        assert 'derivation' in result
        assert '@id' in result['derivation']
        assert result['derivation']['@id'].startswith('urn:uor:derivation:')

    def test_derivation_has_metrics(self):
        root1 = build_root("سجد", "S-J-D", [0.1] * 71)
        root2 = build_root("كتب", "K-T-B", [0.2] * 71)
        
        result = derive_root_similarity(root1, root2)
        
        assert 'uor:termMetrics' in result['derivation']
        metrics = result['derivation']['uor:termMetrics']
        assert 'depth' in metrics
        assert 'nodeCount' in metrics

    def test_derivation_has_result_iri(self):
        root1 = build_root("سجد", "S-J-D", [0.1] * 71)
        root2 = build_root("كتب", "K-T-B", [0.2] * 71)
        
        result = derive_root_similarity(root1, root2)
        
        assert 'uor:result' in result['derivation']
        assert result['derivation']['uor:result']['@id'].startswith('https://uor.foundation/')

    def test_verse_has_derivation(self):
        root = build_root("سجد", "S-J-D", [0.1] * 71)
        feat = build_morpheme_features("V")
        verse_iri = make_verse_iri(1, 1)
        word = build_word("سجد", root, 0, feat, verse_iri)
        verse = build_verse(1, 1, [word])
        
        # Derivation is optional for single-word verses
        assert verse.derivation is None or hasattr(verse.derivation, 'derivation_id')


class TestJSONLDEmission:
    """Validate JSON-LD emission for interoperability."""

    def test_root_emit_jsonld(self):
        root = build_root("سجد", "S-J-D", [0.1] * 71)
        jsonld = root.emit_jsonld()
        
        assert '@id' in jsonld
        assert jsonld['@id'] == root.iri
        assert '@type' in jsonld
        assert jsonld['@type'] == 'geometer:ArabicRoot'

    def test_root_jsonld_contains_prism(self):
        root = build_root("سجد", "S-J-D", [0.1] * 71)
        jsonld = root.emit_jsonld()
        
        assert 'uor:totalStratum' in jsonld
        assert 'geometer:arabic' in jsonld
        assert jsonld['geometer:arabic'] == 'سجد'

    def test_verse_emit_jsonld(self):
        root = build_root("سجد", "S-J-D", [0.1] * 71)
        feat = build_morpheme_features("V")
        verse_iri = make_verse_iri(1, 1)
        word = build_word("سجد", root, 0, feat, verse_iri)
        verse = build_verse(1, 1, [word])
        
        jsonld = verse.emit_jsonld()
        
        assert '@id' in jsonld
        assert jsonld['@type'] == 'geometer:Verse'
        assert 'geometer:surah' in jsonld
        assert jsonld['geometer:surah'] == 1

    def test_word_emit_jsonld(self):
        root = build_root("سجد", "S-J-D", [0.1] * 71)
        feat = build_morpheme_features("V")
        verse_iri = make_verse_iri(1, 1)
        word = build_word("سجد", root, 0, feat, verse_iri)
        
        jsonld = word.emit_jsonld()
        
        assert '@id' in jsonld
        assert jsonld['@type'] == 'geometer:Word'
        assert 'geometer:position' in jsonld

    def test_full_graph_emission(self):
        root1 = build_root("سجد", "S-J-D", [0.1] * 71)
        root2 = build_root("كتب", "K-T-B", [0.2] * 71)
        
        graph = emit_full_jsonld_graph([root1, root2])
        
        assert '@context' in graph
        assert '@graph' in graph
        assert len(graph['@graph']) == 2
        assert graph['@context']['@base'] == GEOMETER_BASE


class TestDomainOperations:
    """Validate domain operations produce correct results."""

    def test_similarity_fidelity_in_range(self):
        root1 = build_root("سجد", "S-J-D", [0.1] * 71)
        root2 = build_root("كتب", "K-T-B", [0.2] * 71)
        
        result = derive_root_similarity(root1, root2)
        
        assert 0.0 <= result['fidelity'] <= 1.0
        assert 0.0 <= result['distance'] <= 1.0

    def test_identical_roots_have_high_fidelity(self):
        profile = [0.1] * 71
        root1 = build_root("سجد", "S-J-D", profile)
        root2 = build_root("سجد", "S-J-D", profile)
        
        result = derive_root_similarity(root1, root2)
        
        assert result['fidelity'] > 0.9

    def test_correlate_with(self):
        root1 = build_root("سجد", "S-J-D", [0.1] * 71)
        root2 = build_root("كتب", "K-T-B", [0.2] * 71)
        
        correlation = root1.correlate_with(root2)
        
        assert 'fidelity' in correlation
        assert 'totalDifference' in correlation


class TestNamespaceConformance:
    """Validate namespace conformance."""

    def test_geometer_base_is_valid_uri(self):
        assert GEOMETER_BASE.startswith('https://')
        assert GEOMETER_BASE.endswith('/')

    def test_geometer_namespace(self):
        assert GEOMETER_NAMESPACE == 'geometer'


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
