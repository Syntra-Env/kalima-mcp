"""Workflow tools: Verification cycles and phase transitions.

Clarified naming:
- word_types: Unique word forms (DNA).
- word_instances: Specific occurrences.
"""

import json
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP

from ..db import get_connection, save_database
from ..utils.features import TERM_TYPE_TO_FEATURE

mcp: FastMCP


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def register(server: FastMCP):
    global mcp
    mcp = server

    @mcp.tool()
    def start_verification(entry_id: str, limit: int = 500) -> dict:
        """Start a new verification workflow for an entry."""
        conn = get_connection()
        row = conn.execute("SELECT * FROM holonomic_entries WHERE address = ?", (entry_id,)).fetchone()
        if not row: return {"success": False, "message": "Entry not found"}

        entry = dict(row)
        if not entry.get('anchor_type') or not entry.get('anchor_ids'):
            return {"success": False, "message": "Entry missing anchors"}

        a_type = entry['anchor_type']
        ids = [i.strip() for i in entry['anchor_ids'].split(',')]
        
        universe = []
        if a_type in ('root', 'lemma', 'morpheme'):
            mapping = TERM_TYPE_TO_FEATURE.get(a_type)
            if mapping:
                db_ft, _ = mapping
                # Map to clarified column names
                fk_col = f"{a_type}_id"
                if a_type == 'morpheme': fk_col = 'morpheme_type_id'
                
                sql = f"""SELECT DISTINCT wi.verse_surah, wi.verse_ayah 
                          FROM morpheme_types mt
                          JOIN word_type_morphemes wtm ON mt.id = wtm.morpheme_type_id
                          JOIN word_instances wi ON wtm.word_type_id = wi.word_type_id
                          WHERE mt.{fk_col} IN ({','.join(['?']*len(ids))})
                          ORDER BY wi.verse_surah, wi.verse_ayah LIMIT ?"""
                rows = conn.execute(sql, ids + [limit]).fetchall()
                universe = [{"surah": r[0], "ayah": r[1]} for r in rows]

        if not universe: return {"success": False, "message": "No universe found"}

        conn.execute(
            "UPDATE holonomic_entries SET verse_queue=?, verse_current_index=0, last_activity=? WHERE address=?",
            (json.dumps(universe), _now(), entry_id)
        )
        save_database()
        return {"success": True, "total": len(universe)}


    @mcp.tool()
    def continue_verification(entry_id: str) -> dict:
        """Continue verification, returning current verse."""
        conn = get_connection()
        row = conn.execute("SELECT * FROM holonomic_entries WHERE address = ?", (entry_id,)).fetchone()
        if not row or not row['verse_queue']: return {"error": "No active verification"}

        queue = json.loads(row['verse_queue'])
        idx = row['verse_current_index'] or 0
        if idx >= len(queue): return {"completed": True}

        v = queue[idx]
        from ..utils.units import compose_verse_text
        return {"surah": v['surah'], "ayah": v['ayah'], "text": compose_verse_text(conn, v['surah'], v['ayah']), "progress": f"{idx+1}/{len(queue)}"}


    @mcp.tool()
    def submit_verification(entry_id: str, verification: str, notes: str | None = None) -> dict:
        """Submit verification result."""
        conn = get_connection()
        row = conn.execute("SELECT * FROM holonomic_entries WHERE address = ?", (entry_id,)).fetchone()
        if not row or not row['verse_queue']: return {"error": "No active verification"}

        queue = json.loads(row['verse_queue'])
        idx = row['verse_current_index'] or 0
        if idx >= len(queue): return {"error": "Completed"}

        curr = queue[idx]
        now = _now()

        # Create verification sub-entry in holonomic_entries
        import hashlib
        parent_content = row['content'] or ''
        anchor_str = f"{curr['surah']}:{curr['ayah']}"
        new_addr = hashlib.sha256(
            (parent_content + '|' + anchor_str + '|' + verification).encode('utf-8')
        ).hexdigest()

        conn.execute(
            """INSERT OR REPLACE INTO holonomic_entries
               (address, content, phase, category, anchor_type, anchor_ids,
                verification, notes, last_activity)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (new_addr, parent_content, 'validation', row['category'],
             'word_instance', anchor_str, verification,
             notes or f"Verified instance of {entry_id}", now)
        )

        conn.execute("UPDATE holonomic_entries SET verse_current_index=verse_current_index+1, last_activity=? WHERE address=?", (now, entry_id))
        save_database()
        return {"success": True, "next": idx + 1 < len(queue)}
