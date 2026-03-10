"""Holonomic and UOR-based research tools.

Implements 'Resonance' and 'Curvature' metrics for objective interpretation.
"""

import sqlite3
from mcp.server.fastmcp import FastMCP
from ..db import get_connection
from ..utils.addressing import find_by_address, get_address

mcp: FastMCP

def register(server: FastMCP):
    global mcp
    mcp = server

    @mcp.tool()
    def get_resonance_map(entity_type: str, entity_id: str) -> dict:
        \"\"\"Find all 'resonances' (identical content-addressed units) for a given entity.
        
        entity_type: 'word_type', 'morpheme_type', 'verse', 'atom'
        entity_id: The ID of the unit to find resonances for.
        \"\"\"
        conn = get_connection()
        
        # 1. Get the address of the source
        address = get_address(conn, entity_type, entity_id)
        if not address:
            return {"error": f"No content address found for {entity_type} {entity_id}"}
        
        # 2. Find all entities sharing this address (The Manifestation)
        hits = find_by_address(conn, address)
        
        # 3. Resolve locations for word_types or morpheme_types
        resonances = []
        for h in hits:
            h_type = h['entity_type']
            h_id = h['entity_id']
            
            # If it's a word_type, find all occurrences (word_instances)
            if h_type == 'word_type':
                occ = conn.execute(
                    \"\"\"SELECT verse_surah, verse_ayah, word_index, normalized_text 
                       FROM word_instances WHERE word_type_id = ?\"\"\",
                    (h_id,)
                ).fetchall()
                for o in occ:
                    resonances.append({
                        "type": "word_instance",
                        "surah": o['verse_surah'],
                        "ayah": o['verse_ayah'],
                        "index": o['word_index'],
                        "text": o['normalized_text']
                    })
            
            # If it's a morpheme_type, find where it appears in word_types
            elif h_type == 'morpheme_type':
                occ = conn.execute(
                    \"\"\"SELECT wt.id as wt_id, wtm.position, wi.verse_surah, wi.verse_ayah
                       FROM word_type_morphemes wtm
                       JOIN word_types wt ON wt.id = wtm.word_type_id
                       JOIN word_instances wi ON wi.word_type_id = wt.id
                       WHERE wtm.morpheme_type_id = ?\"\"\",
                    (h_id,)
                ).fetchall()
                for o in occ:
                    resonances.append({
                        "type": "morpheme_occurrence",
                        "word_type_id": o['wt_id'],
                        "morpheme_position": o['position'],
                        "location": f"{o['verse_surah']}:{o['verse_ayah']}"
                    })
            
            elif h_type == 'verse':
                resonances.append({"type": "verse", "location": h_id})

        return {
            "source_address": address,
            "resonance_count": len(resonances),
            "resonances": resonances[:100] # Limit for MCP response
        }

    @mcp.tool()
    def compare_interpretations(address: str) -> list[dict]:
        \"\"\"Find all research entries (claims) linked to a specific holonomic address.
        
        This allows comparing different insights docked to the same mathematical unit.
        \"\"\"
        conn = get_connection()
        # Find all entries with this address
        rows = conn.execute(
            \"SELECT * FROM holonomic_entries WHERE address = ?\", (address,)
        ).fetchall()
        
        results = []
        for r in rows:
            results.append(dict(r))
            
        # Also find entries linked to entities sharing this address
        hits = find_by_address(conn, address)
        for h in hits:
            # Check if any entries are anchored to this specific entity_id
            e_rows = conn.execute(
                \"SELECT * FROM holonomic_entries WHERE anchor_type = ? AND anchor_ids LIKE ?\",
                (h['entity_type'], f"%{h['entity_id']}%")
            ).fetchall()
            for er in e_rows:
                d = dict(er)
                if d['address'] != address: # Avoid duplicates
                    results.append(d)
                    
        return results
