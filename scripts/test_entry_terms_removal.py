"""Verify entry_terms removal: all tools still work correctly with scope-based queries."""

import json
import os
import sqlite3
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import get_connection


def test_entry_terms_gone():
    """entry_terms table should not exist."""
    conn = get_connection()
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='entry_terms'"
    ).fetchone()
    assert row is None, "entry_terms table should be gone!"
    print("PASS: entry_terms table does not exist")


def test_scoped_entries():
    """Verify migrated entries have scope."""
    conn = get_connection()
    scoped = conn.execute("SELECT count(*) FROM entries WHERE scope_type IS NOT NULL").fetchone()[0]
    assert scoped >= 15, f"Expected >= 15 scoped entries, got {scoped}"
    print(f"PASS: {scoped} entries have scope")

    # Check specific entries
    root_entries = conn.execute(
        "SELECT id, scope_type, scope_value FROM entries WHERE scope_type = 'root' ORDER BY id"
    ).fetchall()
    print(f"  Root-scoped entries: {len(root_entries)}")
    for r in root_entries:
        print(f"    {r['id']}: {r['scope_value']}")

    pattern_entries = conn.execute(
        "SELECT id, scope_type, scope_value FROM entries WHERE scope_type = 'pattern' ORDER BY id"
    ).fetchall()
    print(f"  Pattern-scoped entries: {len(pattern_entries)}")
    for r in pattern_entries:
        print(f"    {r['id']}: {r['scope_value']}")


def test_get_verse_with_context():
    """get_verse_with_context should still surface related entries via scope."""
    from src.tools.context import register as reg_context
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("test")
    reg_context(server)

    # Call get_verse_with_context for 1:1
    fn = server._tool_manager._tools['get_verse_with_context'].fn
    result = fn(surah=1, ayah=1)

    assert 'verse' in result, "Should have verse key"
    assert 'words_with_context' in result, "Should have words_with_context key"
    assert 'direct_verse_entries' in result, "Should have direct_verse_entries key"
    print(f"PASS: get_verse_with_context(1,1) returned {len(result['words_with_context'])} words, {len(result['direct_verse_entries'])} direct entries")


def test_find_related_entries():
    """find_related_entries should use shared_scope instead of shared_terms."""
    from src.tools.research import register as reg_research
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("test")
    reg_research(server)

    fn = server._tool_manager._tools['find_related_entries'].fn
    # entry_280 has scope_type='root', scope_value='قول'
    result = fn(entry_id="entry_280")

    assert 'shared_scope' in result, "Should have shared_scope key (not shared_terms)"
    assert 'shared_terms' not in result, "Should NOT have shared_terms key"
    print(f"PASS: find_related_entries('entry_280') returned {len(result['shared_scope'])} shared_scope, {len(result['shared_evidence'])} shared_evidence")


def test_get_entry_stats():
    """get_entry_stats should work without entry_terms."""
    from src.tools.research import register as reg_research
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("test")
    reg_research(server)

    fn = server._tool_manager._tools['get_entry_stats'].fn
    result = fn()

    assert 'total_entries' in result, "Should have total_entries"
    assert 'health' in result, "Should have health"
    assert 'orphan_entries' in result['health'], "Should have orphan_entries"
    print(f"PASS: get_entry_stats() returned {result['total_entries']} entries, {result['health']['orphan_entries']} orphans")


def test_create_pattern_interpretation():
    """create_pattern_interpretation should work without entry_terms."""
    from src.tools.linguistic import register as reg_linguistic
    from src.tools.research import register as reg_research
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("test")
    reg_research(server)
    reg_linguistic(server)

    fn = server._tool_manager._tools['create_pattern_interpretation'].fn
    result = fn(
        description="Test pattern: perfect verbs",
        pattern_type="verb_pattern",
        interpretation="Testing entry_terms removal",
        linguistic_features={"pos": "V", "aspect": "PERF"},
        phase="question",
    )

    assert result['success'], f"Should succeed: {result.get('message')}"
    entry_id = result['entry_id']
    print(f"PASS: create_pattern_interpretation created {entry_id}")

    # Verify it has scope set
    conn = get_connection()
    entry = conn.execute("SELECT scope_type, scope_value FROM entries WHERE id = ?", (entry_id,)).fetchone()
    assert entry['scope_type'] == 'pattern', f"Expected scope_type='pattern', got '{entry['scope_type']}'"
    features = json.loads(entry['scope_value'])
    assert features == {"pos": "V", "aspect": "PERF"}, f"Wrong scope_value: {entry['scope_value']}"
    print(f"  scope_type='{entry['scope_type']}', scope_value='{entry['scope_value']}'")

    # Clean up: delete test entry
    conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    conn.commit()
    print(f"  Cleaned up test entry {entry_id}")


def test_link_entry_terms_removed():
    """link_entry_terms tool should no longer be registered."""
    from src.tools.linguistic import register as reg_linguistic
    from src.tools.research import register as reg_research
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("test")
    reg_research(server)
    reg_linguistic(server)

    tool_names = list(server._tool_manager._tools.keys())
    assert 'link_entry_terms' not in tool_names, "link_entry_terms should NOT be registered"
    print(f"PASS: link_entry_terms is not in registered tools")
    print(f"  Registered tools: {', '.join(sorted(tool_names))}")


def test_delete_entry():
    """delete_entry should work without entry_terms references."""
    from src.tools.research import register as reg_research
    from mcp.server.fastmcp import FastMCP

    conn = get_connection()

    # Create a test entry
    from src.utils.short_id import generate_entry_id
    eid = generate_entry_id(conn)
    conn.execute(
        "INSERT INTO entries (id, content, phase, category, created_at, updated_at) VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))",
        (eid, "Test entry for deletion", "question", "uncategorized")
    )
    conn.commit()

    server = FastMCP("test")
    reg_research(server)

    fn = server._tool_manager._tools['delete_entry'].fn
    result = fn(entry_id=eid)
    assert result['success'], f"Delete should succeed: {result.get('message')}"
    print(f"PASS: delete_entry({eid}) succeeded")


if __name__ == "__main__":
    tests = [
        test_entry_terms_gone,
        test_scoped_entries,
        test_get_verse_with_context,
        test_find_related_entries,
        test_get_entry_stats,
        test_create_pattern_interpretation,
        test_link_entry_terms_removed,
        test_delete_entry,
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
