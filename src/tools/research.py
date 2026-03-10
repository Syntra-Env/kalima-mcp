"""Research tools: entries CRUD, evidence, relationships."""

import json
import sqlite3
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from ..db import get_connection, save_database
from ..utils.short_id import generate_entry_id
from ..utils.units import get_entry_anchor, entries_at_verse

mcp: FastMCP

VALID_PHASES = {"question", "hypothesis", "validation", "verified", "rejected"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _augment_entry_dict(conn, d: dict, full: bool = False) -> dict:
    """Resolve unified anchor_ids into human-readable strings.

    full=True includes verification stats (used for get_entry, not search).
    """
    from ..utils.units import compose_word_text

    if not d.get('anchor_type') or not d.get('anchor_ids'):
        return d

    a_type = d['anchor_type']
    ids = [i.strip() for i in d['anchor_ids'].split(',')]
    resolved = []

    if a_type in ('root', 'lemma', 'morpheme', 'surah', 'pos', 'segment_type'):
        for aid in ids:
            row = conn.execute("SELECT lookup_key FROM features WHERE id = ?", (aid,)).fetchone()
            resolved.append(f"{aid} ({row['lookup_key']})" if row else aid)

    elif a_type == 'word_type':
        for aid in ids:
            try:
                text = compose_word_text(conn, int(aid))
                resolved.append(f"{aid} ({text})")
            except: resolved.append(aid)

    elif a_type == 'word_instance':
        for aid in ids:
            row = conn.execute(
                """SELECT word_type_id FROM word_instances WHERE global_index = ? OR id = ? LIMIT 1""",
                (aid, aid)
            ).fetchone()
            if row:
                text = compose_word_text(conn, row['word_type_id'])
                resolved.append(f"{aid} ({text})")
            else: resolved.append(aid)

    d['anchor_resolved'] = resolved

    # Verification stats only for full single-entry lookups
    if full and d.get('content') and d.get('id'):
        row = conn.execute(
            """SELECT
                COUNT(CASE WHEN verification = 'supports' THEN 1 END) as supports,
                COUNT(CASE WHEN verification = 'contradicts' THEN 1 END) as contradicts,
                COUNT(CASE WHEN verification = 'unclear' THEN 1 END) as unclear,
                COUNT(id) as total
               FROM entries WHERE content = ? AND id != ?""",
            (d['content'], d['id'])
        ).fetchone()

        if row and row['total'] > 0:
            d['verification_summary'] = {
                "verified_instances": row['total'],
                "supports": row['supports'],
                "contradicts": row['contradicts'],
                "unclear": row['unclear']
            }

    return d


def register(server: FastMCP):
    global mcp
    mcp = server

    @mcp.tool()
    def search_entries(
        query: str | None = None,
        phase: str | None = None,
        category: str | None = None,
        scope_type: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Search research entries by keyword, phase, or category."""
        conn = get_connection()
        sql = "SELECT id, content, phase, category, anchor_type, anchor_ids FROM entries WHERE 1=1"
        params: list = []

        if query:
            sql += " AND lower(content) LIKE ?"
            params.append(f"%{query.lower()}%")
        if phase:
            sql += " AND phase = ?"
            params.append(phase)
        if category:
            sql += " AND category = ?"
            params.append(category)

        if scope_type:
            if scope_type == 'unanchored':
                sql += " AND anchor_type IS NULL"
            else:
                sql += " AND anchor_type = ?"
                params.append(scope_type)

        sql += " ORDER BY last_activity DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(sql, params).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            # Truncate long content in search results
            if d.get('content') and len(d['content']) > 200:
                d['content'] = d['content'][:200] + '...'
            _augment_entry_dict(conn, d)
            results.append(d)
        return results

    @mcp.tool()
    def get_entry(entry_id: str) -> dict:
        """Get a single entry by its ID."""
        conn = get_connection()
        row = conn.execute("SELECT * FROM entries WHERE id = ?", (entry_id,)).fetchone()
        if not row:
            return {"error": f"Entry {entry_id} not found"}
        return _augment_entry_dict(conn, dict(row), full=True)

    @mcp.tool()
    def get_entry_stats() -> dict:
        """Get database statistics."""
        conn = get_connection()
        total = conn.execute("SELECT count(*) FROM entries").fetchone()[0]
        rows = conn.execute("SELECT phase, count(*) as cnt FROM entries GROUP BY phase").fetchall()
        by_phase = {r['phase']: r['cnt'] for r in rows}
        rows = conn.execute("SELECT category, count(*) as cnt FROM entries GROUP BY category").fetchall()
        by_category = {r['category'] or 'uncategorized': r['cnt'] for r in rows}

        return {
            "total_entries": total,
            "by_phase": by_phase,
            "by_category": by_category,
            "anchoring": [dict(r) for r in conn.execute(
                "SELECT anchor_type, count(*) as cnt FROM entries WHERE anchor_type IS NOT NULL GROUP BY anchor_type"
            ).fetchall()]
        }

    # --- Write tools ---

    @mcp.tool()
    def save_bulk_entries(entries: list[dict]) -> dict:
        """Save one or more research entries in bulk.
        
        Each entry dict should have:
        - content: str (required)
        - phase: str (optional, default: "question")
        - category: str (optional, default: "uncategorized")
        - anchor_type: str (optional)
        - anchor_ids: str (optional)
        - notes: str (optional)
        
        Returns list of created entry IDs.
        """
        conn = get_connection()
        created = []
        errors = []
        
        for i, entry in enumerate(entries):
            phase = entry.get('phase', 'question')
            if phase not in VALID_PHASES:
                errors.append({"index": i, "error": f"Invalid phase '{phase}'"})
                continue
            
            try:
                entry_id = generate_entry_id(conn)
                conn.execute(
                    """INSERT INTO entries (
                        id, content, phase, category, anchor_type, anchor_ids, notes, last_activity
                       )
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        entry_id,
                        entry.get('content', ''),
                        phase,
                        entry.get('category', 'uncategorized'),
                        entry.get('anchor_type'),
                        entry.get('anchor_ids'),
                        entry.get('notes'),
                        _now()
                    )
                )
                created.append(entry_id)
            except Exception as e:
                errors.append({"index": i, "error": str(e)})
        
        if created:
            save_database()
        
        return {
            "success": len(created) > 0,
            "created_count": len(created),
            "created_ids": created,
            "error_count": len(errors),
            "errors": errors if errors else None
        }

    @mcp.tool()
    def update_entry(
        entry_id: str,
        content: str | None = None,
        phase: str | None = None,
        anchor_type: str | None = None,
        anchor_ids: str | None = None,
        category: str | None = None,
        notes: str | None = None,
    ) -> dict:
        """Update an existing entry's content, phase, or anchors."""
        conn = get_connection()
        try:
            updates = ["last_activity = ?"]
            params = [_now()]

            if content: updates.append("content = ?"); params.append(content)
            if phase: updates.append("phase = ?"); params.append(phase)
            if category: updates.append("category = ?"); params.append(category)
            if anchor_type: updates.append("anchor_type = ?"); params.append(anchor_type)
            if anchor_ids: updates.append("anchor_ids = ?"); params.append(anchor_ids)
            if notes: updates.append("notes = ?"); params.append(notes)

            params.append(entry_id)
            conn.execute(f"UPDATE entries SET {', '.join(updates)} WHERE id = ?", params)
            save_database()
            return {"success": True}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def delete_entry(entry_id: str) -> dict:
        """Delete an entry."""
        conn = get_connection()
        conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
        save_database()
        return {"success": True}
