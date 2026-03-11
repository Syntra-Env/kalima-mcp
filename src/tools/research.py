"""Research Tool (v2): Claims and Docking.

Handles the 'Interpretive Field'. Claims are docked to Manifold Addresses.
"""

import sqlite3
import hashlib
from datetime import datetime, timezone
from mcp.server.fastmcp import FastMCP
from src.db import get_connection, save_database
from src.utils.addressing import find_by_address, get_address

mcp: FastMCP

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def dock_claim(content: str, anchor_address: str, category: str = "general", phase: str = "question") -> dict:
    """Dock a research claim to a specific Manifold Address.
    
    This locks the insight to the mathematical identity of the text.
    """
    conn = get_connection()
    
    # 1. Compute entry address
    # (Content | Anchor_Address)
    canonical = content.encode('utf-8') + b'|' + anchor_address.encode('ascii')
    entry_addr = hashlib.sha256(canonical).hexdigest()
    
    # 2. Get anchor info
    hits = find_by_address(conn, anchor_address)
    anchor_type = hits[0]['entity_type'] if hits else 'unknown'
    anchor_id = hits[0]['entity_id'] if hits else 'unknown'

    # 3. Store in holonomic_entries
    conn.execute(
        """INSERT OR REPLACE INTO holonomic_entries (
            address, content, phase, category, anchor_type, anchor_ids, last_activity
           ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (entry_addr, content, phase, category, anchor_type, anchor_id, _now())
    )
    
    # 4. Link in content_addresses
    conn.execute(
        """INSERT OR REPLACE INTO content_addresses (entity_type, entity_id, address) 
           VALUES (?, ?, ?)""",
        ('holonomic_entry', entry_addr, entry_addr)
    )
    
    save_database()
    return {
        "entry_address": entry_addr,
        "anchored_to": anchor_address,
        "type": anchor_type
    }

def register(server: FastMCP):
    global mcp
    mcp = server

    @mcp.tool()
    def dock_claim_tool(content: str, anchor_address: str, category: str = "general", phase: str = "question") -> dict:
        """Dock a research claim to a specific Manifold Address."""
        return dock_claim(content, anchor_address, category, phase)

    @mcp.tool()
    def search_research(query: str, limit: int = 20) -> list[dict]:
        """Search for research claims docked in the manifold."""
        conn = get_connection()
        sql = """SELECT address, content, phase, category, anchor_type, anchor_ids 
                  FROM holonomic_entries WHERE content LIKE ? 
                  ORDER BY last_activity DESC LIMIT ?"""
        rows = conn.execute(sql, (f"%{query}%", limit)).fetchall()
        return [dict(r) for r in rows]

    @mcp.tool()
    def get_entry_details(address: str) -> dict:
        """Get full details of a research entry by its address."""
        conn = get_connection()
        row = conn.execute("SELECT * FROM holonomic_entries WHERE address = ?", (address,)).fetchone()
        if not row:
            return {"error": "Entry not found"}
        
        d = dict(row)
        anchor_addr = get_address(conn, d['anchor_type'], d['anchor_ids'])
        d['anchor_address'] = anchor_addr
        return d
