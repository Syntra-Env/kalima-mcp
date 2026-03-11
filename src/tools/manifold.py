"""Manifold Tool: Identity and Composition.

The core of the Holonomic system. Every entity is accessed via its 
UOR Content Address (SHA-256).
"""

import sqlite3
from mcp.server.fastmcp import FastMCP
from ..db import get_connection
from ..utils.addressing import get_address, find_by_address

mcp: FastMCP

def register(server: FastMCP):
    global mcp
    mcp = server

    @mcp.tool()
    def resolve_address(address: str) -> dict:
        """The 'Universal Key'. Resolve any UOR address into its type and data."""
        conn = get_connection()
        
        # 1. Identify what this address represents
        hits = find_by_address(conn, address)
        if not hits:
            return {"error": f"Address {address} not found in manifold."}
            
        results = []
        for h in hits:
            e_type = h['entity_type']
            e_id = h['entity_id']
            
            # 2. Fetch the corresponding data based on type
            data = {"type": e_type, "id": e_id}
            
            if e_type == 'holonomic_entry':
                row = conn.execute("SELECT * FROM holonomic_entries WHERE address = ?", (address,)).fetchone()
                if row: data.update(dict(row))
                
            elif e_type == 'word_type':
                from ..utils.units import compose_word_text
                data['text'] = compose_word_text(conn, int(e_id))
                
            elif e_type == 'morpheme_type':
                row = conn.execute("SELECT uthmani_text, root_id FROM morpheme_types WHERE id = ?", (e_id,)).fetchone()
                if row:
                    data['text'] = row['uthmani_text']
                    data['root_id'] = row['root_id']
            
            elif e_type == 'verse':
                # e_id is 'surah:ayah'
                s, a = e_id.split(':')
                row = conn.execute("SELECT text FROM verses WHERE surah = ? AND ayah = ?", (s, a)).fetchone()
                if row: data['text'] = row['text']

            results.append(data)
            
        return {
            "address": address,
            "resolutions": results
        }

    @mcp.tool()
    def get_composition(address: str) -> dict:
        """Explode an address into its constituent UOR addresses (Bottom-Up).
        
        Example: Word -> Morphemes -> Atoms.
        """
        conn = get_connection()
        hits = find_by_address(conn, address)
        if not hits:
            return {"error": "Address not found"}
            
        comp = []
        for h in hits:
            e_type = h['entity_type']
            e_id = h['entity_id']
            
            if e_type == 'word_type':
                # Get morpheme addresses
                rows = conn.execute(
                    """SELECT wtm.morpheme_type_id, ca.address 
                       FROM word_type_morphemes wtm
                       JOIN content_addresses ca ON ca.entity_id = wtm.morpheme_type_id 
                       AND ca.entity_type = 'morpheme_type'
                       WHERE wtm.word_type_id = ? ORDER BY wtm.position""",
                    (e_id,)
                ).fetchall()
                comp.append({
                    "type": "word_composition",
                    "morphemes": [dict(r) for r in rows]
                })
                
            elif e_type == 'morpheme_type':
                # Get atom addresses
                rows = conn.execute(
                    """SELECT ma.id, ca.address, ma.base_letter, ma.diacritics
                       FROM morpheme_atoms ma
                       JOIN content_addresses ca ON ca.entity_id = ma.id 
                       AND ca.entity_type = 'atom'
                       WHERE ma.morpheme_type_id = ? ORDER BY ma.position""",
                    (e_id,)
                ).fetchall()
                comp.append({
                    "type": "morpheme_composition",
                    "atoms": [dict(r) for r in rows]
                })
                
            elif e_type == 'verse':
                # Get word instance addresses
                s, a = e_id.split(':')
                rows = conn.execute(
                    """SELECT wi.global_index, ca.address, wi.normalized_text
                       FROM word_instances wi
                       JOIN content_addresses ca ON ca.entity_id = wi.id 
                       AND ca.entity_type = 'word_instance'
                       WHERE wi.verse_surah = ? AND wi.verse_ayah = ?
                       ORDER BY wi.word_index""",
                    (s, a)
                ).fetchall()
                comp.append({
                    "type": "verse_composition",
                    "words": [dict(r) for r in rows]
                })

        return {
            "address": address,
            "composition": comp
        }
