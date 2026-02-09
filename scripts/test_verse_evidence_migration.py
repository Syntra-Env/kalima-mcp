"""Verify verse_evidence migration: all tools work correctly after migration."""

import io
import sys
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db import get_connection


def test_verse_evidence_table_gone():
    """verse_evidence table should NOT exist."""
    conn = get_connection()
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert 'verse_evidence' not in tables, "verse_evidence table still exists!"
    print("PASS: verse_evidence table confirmed removed")


def test_verse_scoped_entries_exist():
    """Should have 122 verse-scoped entries from migration."""
    conn = get_connection()
    count = conn.execute("SELECT count(*) FROM entries WHERE scope_type = 'verse'").fetchone()[0]
    assert count >= 122, f"Expected >= 122 verse-scoped entries, got {count}"
    print(f"PASS: {count} verse-scoped entries exist")


def test_verse_entries_have_dependencies():
    """Every verse-scoped entry should have at least one dependency link."""
    conn = get_connection()
    orphans = conn.execute("""
        SELECT count(*) FROM entries e
        WHERE e.scope_type = 'verse'
          AND e.id NOT IN (SELECT entry_id FROM entry_dependencies)
    """).fetchone()[0]
    assert orphans == 0, f"{orphans} verse-scoped entries have no dependency link!"
    print("PASS: All verse-scoped entries have dependency links")


def test_get_entry_evidence():
    """get_entry_evidence should return verse-scoped children."""
    from src.tools.research import register as reg_research
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("test")
    reg_research(server)

    fn = server._tool_manager._tools['get_entry_evidence'].fn

    # entry_237 had 4 verse_evidence rows with notes
    result = fn(entry_id="entry_237")
    assert len(result) >= 4, f"Expected >= 4 evidence for entry_237, got {len(result)}"
    # Check structure
    first = result[0]
    assert 'surah' in first, "Should have surah"
    assert 'ayah' in first, "Should have ayah"
    assert 'verification' in first, "Should have verification"
    assert 'notes' in first, "Should have notes"
    print(f"PASS: get_entry_evidence(entry_237) returned {len(result)} evidence entries")


def test_get_verse_entries():
    """get_verse_entries should find verse-scoped entries for a verse."""
    from src.tools.research import register as reg_research
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("test")
    reg_research(server)

    fn = server._tool_manager._tools['get_verse_entries'].fn

    # 1:5 had evidence from entry_237 (supports)
    result = fn(surah=1, ayah=5)
    assert len(result) > 0, "Should find verse entries for 1:5"
    print(f"PASS: get_verse_entries(1,5) returned {len(result)} entries")


def test_get_entry_stats():
    """get_entry_stats should work without verse_evidence table."""
    from src.tools.research import register as reg_research
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("test")
    reg_research(server)

    fn = server._tool_manager._tools['get_entry_stats'].fn
    result = fn()

    assert 'total_entries' in result, "Should have total_entries"
    assert 'total_evidence' in result, "Should have total_evidence"
    assert result['total_entries'] > 0, "Should have entries"
    assert result['total_evidence'] >= 122, f"Should have >= 122 evidence, got {result['total_evidence']}"
    print(f"PASS: get_entry_stats returned {result['total_entries']} entries, {result['total_evidence']} evidence")


def test_get_verse_with_context():
    """get_verse_with_context should use entry-based queries."""
    from src.tools.context import register as reg_context
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("test")
    reg_context(server)

    fn = server._tool_manager._tools['get_verse_with_context'].fn
    result = fn(surah=1, ayah=5)

    assert 'verse' in result, "Should have verse key"
    assert 'direct_verse_entries' in result, "Should have direct_verse_entries"
    # 1:5 had evidence, should be found
    assert len(result['direct_verse_entries']) > 0, "Should have direct entries for 1:5"
    print(f"PASS: get_verse_with_context(1,5) returned {len(result['direct_verse_entries'])} direct entries")


def test_find_related_entries():
    """find_related_entries should work with entry-based evidence."""
    from src.tools.research import register as reg_research
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("test")
    reg_research(server)

    fn = server._tool_manager._tools['find_related_entries'].fn

    # entry_241 had 18 verse evidence entries
    result = fn(entry_id="entry_241")
    assert 'entry' in result, "Should have entry"
    assert result['entry'] is not None, "entry_241 should exist"
    print(f"PASS: find_related_entries(entry_241) returned shared_evidence={len(result['shared_evidence'])}, shared_scope={len(result['shared_scope'])}")


def test_delete_entry():
    """delete_entry should clean up verse-scoped children."""
    from src.tools.research import register as reg_research
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("test")
    reg_research(server)

    save_fn = server._tool_manager._tools['save_entry'].fn
    delete_fn = server._tool_manager._tools['delete_entry'].fn

    # Create a test entry with evidence
    result = save_fn(
        content="Test entry for delete verification",
        evidence_verses=[{"surah": 112, "ayah": 1, "notes": "Test evidence note"}],
    )
    assert result['success'], f"Failed to save: {result['message']}"
    test_id = result['entry_id']

    conn = get_connection()
    # Verify child exists
    children = conn.execute(
        """SELECT ed.entry_id FROM entry_dependencies ed
           JOIN entries e ON e.id = ed.entry_id
           WHERE ed.depends_on_entry_id = ? AND e.scope_type = 'verse'""",
        (test_id,)
    ).fetchall()
    assert len(children) == 1, f"Expected 1 child, got {len(children)}"

    child_id = children[0]['entry_id']

    # Delete parent
    del_result = delete_fn(entry_id=test_id)
    assert del_result['success'], f"Failed to delete: {del_result['message']}"

    # Verify parent and child are both gone
    assert conn.execute("SELECT id FROM entries WHERE id = ?", (test_id,)).fetchone() is None
    assert conn.execute("SELECT id FROM entries WHERE id = ?", (child_id,)).fetchone() is None
    print(f"PASS: delete_entry cleaned up parent + verse-scoped child")


if __name__ == "__main__":
    tests = [
        test_verse_evidence_table_gone,
        test_verse_scoped_entries_exist,
        test_verse_entries_have_dependencies,
        test_get_entry_evidence,
        test_get_verse_entries,
        test_get_entry_stats,
        test_get_verse_with_context,
        test_find_related_entries,
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
