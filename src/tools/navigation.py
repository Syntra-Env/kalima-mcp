"""Navigation Tool: Space-Time/Locations.

Maps between UOR addresses (Identity) and Verse Coordinates (Location).
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
    def locate_identity(address: str) -> dict:
        """Find all Quranic locations where a specific content address manifests."""
        conn = get_connection()
        hits = find_by_address(conn, address)
        if not hits:
            return {"error": "Address not found"}
            
        locations = []
        for h in hits:
            e_type = h['entity_type']
            e_id = h['entity_id']
            
            if e_type == 'word_type':
                rows = conn.execute(
                    """SELECT verse_surah, verse_ayah, word_index, normalized_text 
                       FROM word_instances WHERE word_type_id = ?""", (e_id,)
                ).fetchall()
                for r in rows:
                    locations.append({
                        "type": "word_instance",
                        "surah": r['verse_surah'],
                        "ayah": r['verse_ayah'],
                        "index": r['word_index'],
                        "text": r['normalized_text']
                    })
            
            elif e_type == 'morpheme_type':
                rows = conn.execute(
                    """SELECT wi.verse_surah, wi.verse_ayah, wi.word_index, wi.normalized_text
                       FROM word_type_morphemes wtm
                       JOIN word_instances wi ON wi.word_type_id = wtm.word_type_id
                       WHERE wtm.morpheme_type_id = ?""", (e_id,)
                ).fetchall()
                for r in rows:
                    locations.append({
                        "type": "morpheme_occurrence",
                        "surah": r['verse_surah'],
                        "ayah": r['verse_ayah'],
                        "index": r['word_index'],
                        "text": r['normalized_text']
                    })

            elif e_type == 'verse':
                locations.append({"type": "verse", "id": e_id})

        return {
            "address": address,
            "locations": locations
        }

    @mcp.tool()
    def get_verse_lattice(surah: int, ayah: int) -> dict:
        """Get a verse as a lattice of UOR addresses (Bottom-Up View)."""
        conn = get_connection()
        
        # 1. Get the verse address
        verse_addr = get_address(conn, 'verse', f"{surah}:{ayah}")
        
        # 2. Get the word instances
        rows = conn.execute(
            """SELECT wi.id, wi.word_index, wi.normalized_text, ca.address as word_instance_addr
               FROM word_instances wi
               JOIN content_addresses ca ON ca.entity_id = wi.id AND ca.entity_type = 'word_instance'
               WHERE wi.verse_surah = ? AND wi.verse_ayah = ?
               ORDER BY wi.word_index""",
            (surah, ayah)
        ).fetchall()
        
        word_chain = []
        for r in rows:
            # For each word instance, also get its type address
            wt_id = conn.execute("SELECT word_type_id FROM word_instances WHERE id = ?", (r['id'],)).fetchone()[0]
            wt_addr = get_address(conn, 'word_type', str(wt_id))
            
            word_chain.append({
                "index": r['word_index'],
                "text": r['normalized_text'],
                "instance_address": r['word_instance_addr'],
                "type_address": wt_addr
            })

        return {
            "surah": surah,
            "ayah": ayah,
            "verse_address": verse_addr,
            "lattice": word_chain
        }
