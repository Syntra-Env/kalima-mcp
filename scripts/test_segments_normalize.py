"""Verify segments normalization: all tools work correctly with FK-based queries."""

import io
import json
import sys
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

from kalima.db import get_connection


def test_segments_schema():
    """Segments table should have *_id FK columns, not text columns."""
    conn = get_connection()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(segments)").fetchall()}

    # FK columns should exist
    for fk in ['root_id', 'lemma_id', 'pos_id', 'verb_form_id', 'voice_id', 'mood_id',
               'aspect_id', 'person_id', 'number_id', 'gender_id', 'case_value_id',
               'dependency_rel_id', 'derived_noun_type_id', 'state_id', 'role_id', 'type_id']:
        assert fk in cols, f"Missing FK column: {fk}"

    # Old text columns should NOT exist
    for old in ['root', 'lemma', 'pos', 'verb_form', 'voice', 'mood', 'aspect',
                'person', 'number', 'gender', 'case_value', 'dependency_rel',
                'derived_noun_type', 'state', 'role', 'type']:
        assert old not in cols, f"Old text column still exists: {old}"

    # Non-FK columns should still exist
    for keep in ['id', 'token_id', 'form']:
        assert keep in cols, f"Missing non-FK column: {keep}"

    print(f"PASS: segments has {len(cols)} columns with correct FK structure")


def test_fk_integrity():
    """Every non-NULL FK in segments should point to a valid ref_features row."""
    conn = get_connection()
    fk_cols = ['root_id', 'lemma_id', 'pos_id', 'verb_form_id', 'voice_id', 'mood_id',
               'aspect_id', 'person_id', 'number_id', 'gender_id', 'case_value_id',
               'dependency_rel_id', 'derived_noun_type_id', 'state_id', 'role_id', 'type_id']

    for fk in fk_cols:
        orphans = conn.execute(f"""
            SELECT count(*) FROM segments s
            WHERE s.{fk} IS NOT NULL
            AND s.{fk} NOT IN (SELECT id FROM ref_features)
        """).fetchone()[0]
        assert orphans == 0, f"{fk} has {orphans} orphan FKs!"

    print("PASS: All FK columns have valid ref_features references")


def test_no_null_pos():
    """pos_id should never be NULL (every segment has a POS)."""
    conn = get_connection()
    null_count = conn.execute("SELECT count(*) FROM segments WHERE pos_id IS NULL").fetchone()[0]
    assert null_count == 0, f"Expected 0 NULL pos_id, got {null_count}"
    print("PASS: No NULL pos_id values")


def test_search_by_linguistic_features():
    """search_by_linguistic_features should work with FK-based queries."""
    from kalima.tools.linguistic import register as reg_linguistic
    from kalima.tools.research import register as reg_research
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("test")
    reg_research(server)
    reg_linguistic(server)

    fn = server._tool_manager._tools['search_by_linguistic_features'].fn

    # Search by root
    result = fn(root="قول", limit=5)
    assert 'error' not in result, f"Error: {result.get('error')}"
    assert result['query_info']['verses_returned'] > 0, "Should find verses with root قول"
    # Check segments in result have resolved text values
    first = result['result'][0]
    assert len(first['segments']) > 0, "Should have segments"
    seg = first['segments'][0]
    assert 'root' in seg, "Segment should have 'root' key (resolved from FK)"
    print(f"PASS: search_by_linguistic_features(root=قول) returned {result['query_info']['verses_returned']} verses")

    # Search by POS + aspect
    result2 = fn(pos="V", aspect="IMPF", limit=3)
    assert 'error' not in result2, f"Error: {result2.get('error')}"
    assert result2['query_info']['verses_returned'] > 0
    print(f"PASS: search_by_linguistic_features(pos=V, aspect=IMPF) returned {result2['query_info']['verses_returned']} verses")


def test_compare_roots():
    """compare_roots should work with FK-based queries."""
    from kalima.tools.linguistic import register as reg_linguistic
    from kalima.tools.research import register as reg_research
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("test")
    reg_research(server)
    reg_linguistic(server)

    fn = server._tool_manager._tools['compare_roots'].fn
    result = fn(root1="قول", root2="سمع", limit=5)

    assert 'error' not in result, f"Error: {result.get('error')}"
    assert result['total_co_occurrences'] > 0, "Should find co-occurrences"
    assert len(result['co_occurrences']) > 0
    # Check word resolution
    co = result['co_occurrences'][0]
    assert len(co['root1_words']) > 0, "Should have root1 words"
    assert len(co['root2_words']) > 0, "Should have root2 words"
    print(f"PASS: compare_roots(قول, سمع) found {result['total_co_occurrences']} co-occurrences")


def test_get_verse_with_context():
    """get_verse_with_context should resolve FK columns to text."""
    from kalima.tools.context import register as reg_context
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("test")
    reg_context(server)

    fn = server._tool_manager._tools['get_verse_with_context'].fn
    result = fn(surah=1, ayah=1)

    assert 'verse' in result, "Should have verse key"
    assert 'words_with_context' in result, "Should have words_with_context key"
    assert len(result['words_with_context']) > 0, "Should have words"

    # Check that words have resolved feature values (not IDs)
    word = result['words_with_context'][0]
    assert 'pos' in word, "Word should have 'pos' key"
    # pos value should be text like 'N', 'V', etc., not an integer
    if word['pos'] is not None:
        assert isinstance(word['pos'], str), f"pos should be string, got {type(word['pos'])}: {word['pos']}"

    print(f"PASS: get_verse_with_context(1,1) returned {len(result['words_with_context'])} words")


def test_compute_verse_universe():
    """compute_verse_universe should work with FK-based queries."""
    from kalima.tools.workflow import compute_verse_universe

    conn = get_connection()

    # Root scope
    verses = compute_verse_universe(conn, 'root', 'قول', limit=10)
    assert len(verses) > 0, "Should find verses for root قول"
    print(f"PASS: compute_verse_universe('root', 'قول') returned {len(verses)} verses")

    # Pattern scope
    features_json = json.dumps({"pos": "V", "aspect": "IMPF"})
    verses2 = compute_verse_universe(conn, 'pattern', features_json, limit=10)
    assert len(verses2) > 0, "Should find verses for V+IMPF pattern"
    print(f"PASS: compute_verse_universe('pattern', V+IMPF) returned {len(verses2)} verses")


def test_ref_features_completeness():
    """Every unique FK value in segments should correspond to a ref_features row."""
    conn = get_connection()

    fk_cols = ['root_id', 'lemma_id', 'pos_id', 'verb_form_id', 'voice_id', 'mood_id',
               'aspect_id', 'person_id', 'number_id', 'gender_id', 'case_value_id',
               'dependency_rel_id', 'derived_noun_type_id', 'state_id', 'role_id', 'type_id']

    total_unique = 0
    for fk in fk_cols:
        unique = conn.execute(f"SELECT count(DISTINCT {fk}) FROM segments WHERE {fk} IS NOT NULL").fetchone()[0]
        total_unique += unique

    ref_total = conn.execute("SELECT count(*) FROM ref_features").fetchone()[0]
    print(f"PASS: {total_unique} unique FK values across segments, {ref_total} ref_features rows")


if __name__ == "__main__":
    tests = [
        test_segments_schema,
        test_fk_integrity,
        test_no_null_pos,
        test_search_by_linguistic_features,
        test_compare_roots,
        test_get_verse_with_context,
        test_compute_verse_universe,
        test_ref_features_completeness,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            print(f"\n--- {test.__name__} ---")
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")
    if failed:
        sys.exit(1)
