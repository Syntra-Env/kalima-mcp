"""Research tools: entries CRUD, evidence, relationships.

Transitions to Holonomic Manifold Model (Content Addressing as Primary Identity).
"""

import json
import sqlite3
import hashlib
from datetime import datetime, timezone

from mcp.server.fastmcp import FastMCP

from ..db import get_connection, save_database
from ..utils.short_id import generate_entry_id
from ..utils.units import get_entry_anchor, entries_at_verse
from ..utils.addressing import update_entry_address, find_by_address, get_address

mcp: FastMCP

VALID_PHASES = {"question", "hypothesis", "validation", "verified", "rejected"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _augment_entry_dict(conn, d: dict, full: bool = False) -> dict:
    """Resolve unified anchor_ids into human-readable strings."""
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

    # Verification stats
    if full and d.get('content') and d.get('address'):
        row = conn.execute(
            """SELECT
                COUNT(CASE WHEN verification = 'supports' THEN 1 END) as supports,
                COUNT(CASE WHEN verification = 'contradicts' THEN 1 END) as contradicts,
                COUNT(CASE WHEN verification = 'unclear' THEN 1 END) as unclear,
                COUNT(address) as total
               FROM holonomic_entries WHERE content = ? AND address != ?""",
            (d['content'], d['address'])
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
        sql = "SELECT address, content, phase, category, anchor_type, anchor_ids FROM holonomic_entries WHERE 1=1"
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
            if d.get('content') and len(d['content']) > 200:
                d['content'] = d['content'][:200] + '...'
            _augment_entry_dict(conn, d)
            results.append(d)
        return results

    @mcp.tool()
    def get_entry(entry_id: str) -> dict:
        """Get a single entry by its address or legacy short_id."""
        conn = get_connection()
        # 1. Try address
        row = conn.execute("SELECT * FROM holonomic_entries WHERE address = ?", (entry_id,)).fetchone()
        
        # 2. Try legacy short_id
        if not row:
            row = conn.execute(
                """SELECT h.* FROM holonomic_entries h
                   JOIN content_addresses ca ON ca.address = h.address
                   WHERE ca.entity_id = ? AND ca.entity_type = 'entry'""",
                (entry_id,)
            ).fetchone()
            
        if not row:
            return {"error": f"Entry {entry_id} not found"}
        return _augment_entry_dict(conn, dict(row), full=True)

    @mcp.tool()
    def get_content_address(entity_type: str, entity_id: str) -> dict:
        """Get the UOR content address for any entity (verse, word_type, entry, etc)."""
        conn = get_connection()
        addr = get_address(conn, entity_type, entity_id)
        return {"entity_type": entity_type, "entity_id": entity_id, "address": addr}

    @mcp.tool()
    def find_by_content_address(address: str) -> list[dict]:
        """Find all entities (including research entries) matching a UOR address."""
        conn = get_connection()
        hits = find_by_address(conn, address)
        results = []
        for h in hits:
            if h['entity_type'] == 'entry':
                row = conn.execute("SELECT * FROM holonomic_entries WHERE address = ?", (h['address'],)).fetchone()
                if not row: # Try by entity_id link
                     row = conn.execute("SELECT * FROM holonomic_entries WHERE address = ?", (address,)).fetchone()
                if row:
                    results.append({"type": "entry", "data": _augment_entry_dict(conn, dict(row))})
            else:
                results.append({"type": h['entity_type'], "id": h['entity_id']})
        return results

    @mcp.tool()
    def get_entry_stats() -> dict:
        """Get database statistics."""
        conn = get_connection()
        total = conn.execute("SELECT count(*) FROM holonomic_entries").fetchone()[0]
        rows = conn.execute("SELECT phase, count(*) as cnt FROM holonomic_entries GROUP BY phase").fetchall()
        by_phase = {r['phase']: r['cnt'] for r in rows}
        rows = conn.execute("SELECT category, count(*) as cnt FROM holonomic_entries GROUP BY category").fetchall()
        by_category = {r['category'] or 'uncategorized': r['cnt'] for r in rows}

        return {
            "total_entries": total,
            "by_phase": by_phase,
            "by_category": by_category,
            "anchoring": [dict(r) for r in conn.execute(
                "SELECT anchor_type, count(*) as cnt FROM holonomic_entries WHERE anchor_type IS NOT NULL GROUP BY anchor_type"
            ).fetchall()]
        }

    # --- Write tools ---

    @mcp.tool()
    def save_bulk_entries(entries: list[dict]) -> dict:
        """Save research entries using UOR content addresses as primary identity."""
        conn = get_connection()
        created = []
        errors = []
        
        for i, entry in enumerate(entries):
            phase = entry.get('phase', 'question')
            if phase not in VALID_PHASES:
                errors.append({"index": i, "error": f"Invalid phase '{phase}'"})
                continue
            
            try:
                content = entry.get('content', '')
                a_type = entry.get('anchor_type')
                a_ids = entry.get('anchor_ids')
                
                # Compute UOR address
                canonical = b'|'.join([
                    (content or '').encode('utf-8'),
                    (a_type or '').encode('ascii'),
                    (a_ids or '').encode('ascii')
                ])
                address = hashlib.sha256(canonical).hexdigest()

                conn.execute(
                    """INSERT OR REPLACE INTO holonomic_entries (
                        address, content, phase, category, anchor_type, anchor_ids, notes, last_activity
                       )
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        address,
                        content,
                        phase,
                        entry.get('category', 'uncategorized'),
                        a_type,
                        a_ids,
                        entry.get('notes'),
                        _now()
                    )
                )
                
                # Maintain legacy mapping link
                entry_id = generate_entry_id(conn)
                conn.execute(
                    "INSERT OR REPLACE INTO content_addresses (entity_type, entity_id, address) VALUES (?, ?, ?)",
                    ('entry', entry_id, address)
                )
                
                created.append(address)
            except Exception as e:
                errors.append({"index": i, "error": str(e)})
        
        if created:
            save_database()
        
        return {
            "success": len(created) > 0,
            "created_count": len(created),
            "addresses": created,
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
        """Update an existing entry. Identity shift (content/anchor change) creates new address."""
        conn = get_connection()
        try:
            # 1. Find existing
            row = conn.execute("SELECT * FROM holonomic_entries WHERE address = ?", (entry_id,)).fetchone()
            if not row:
                row = conn.execute(
                    """SELECT h.* FROM holonomic_entries h 
                       JOIN content_addresses ca ON ca.address = h.address 
                       WHERE ca.entity_id = ?""", (entry_id,)
                ).fetchone()
            
            if not row:
                return {"success": False, "message": "Entry not found"}
            
            old_address = row['address']
            
            # 2. Prepare new values
            new_content = content if content is not None else row['content']
            new_a_type = anchor_type if anchor_type is not None else row['anchor_type']
            new_a_ids = anchor_ids if anchor_ids is not None else row['anchor_ids']
            
            # 3. Compute new address
            canonical = b'|'.join([
                (new_content or '').encode('utf-8'),
                (new_a_type or '').encode('ascii'),
                (new_a_ids or '').encode('ascii')
            ])
            new_address = hashlib.sha256(canonical).hexdigest()
            
            # 4. If identity changed, delete old
            if new_address != old_address:
                conn.execute("DELETE FROM holonomic_entries WHERE address = ?", (old_address,))
            
            # 5. Insert/Update
            conn.execute(
                """INSERT OR REPLACE INTO holonomic_entries (
                    address, content, phase, category, anchor_type, anchor_ids, notes, last_activity
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    new_address,
                    new_content,
                    phase if phase is not None else row['phase'],
                    category if category is not None else row['category'],
                    new_a_type,
                    new_a_ids,
                    notes if notes is not None else row['notes'],
                    _now()
                )
            )
            
            save_database()
            return {"success": True, "new_address": new_address}
        except Exception as e:
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def delete_entry(entry_id: str) -> dict:
        """Delete an entry by address or legacy ID."""
        conn = get_connection()
        # Try address
        res = conn.execute("DELETE FROM holonomic_entries WHERE address = ?", (entry_id,))
        if res.rowcount == 0:
            # Try legacy link
            row = conn.execute("SELECT address FROM content_addresses WHERE entity_id = ? AND entity_type = 'entry'", (entry_id,)).fetchone()
            if row:
                conn.execute("DELETE FROM holonomic_entries WHERE address = ?", (row['address'],))
        
        save_database()
        return {"success": True}
