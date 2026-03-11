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
        anchor_type = d.get('anchor_type')
        anchor_ids = d.get('anchor_ids')
        if anchor_type and anchor_ids:
            anchor_addr = get_address(conn, anchor_type, str(anchor_ids))
        else:
            anchor_addr = None
        d['anchor_address'] = anchor_addr
        return d

    @mcp.tool()
    def classify_monodromy(address: str) -> dict:
        \"\"\"Classify an interpretation as FlatType or TwistedType (P3.9).
        
        Flat = consistent meaning everywhere (Low holonomy variance).
        Twisted = meaning shifts by context (Non-trivial monodromy).
        \"\"\"
        import numpy as np
        conn = get_connection()
        row = conn.execute(\"SELECT anchor_type, anchor_ids FROM holonomic_entries WHERE address = ?\", (address,)).fetchone()
        if not row:
            return {\"error\": \"Entry not found\"}
            
        anchor_type = row['anchor_type']
        anchor_ids = row['anchor_ids']
        if not anchor_type or not anchor_ids:
            return {\"error\": \"Interpretation has no anchor to measure.\"}

        # 1. Find resonances of the anchor
        from .analytics import measure_manifold_curvature
        from src.utils.addressing import find_by_address, get_address
        
        anchor_addr = get_address(conn, anchor_type, str(anchor_ids))
        if not anchor_addr:
            return {\"error\": \"Anchor address not found\"}
            
        hits = find_by_address(conn, anchor_addr)
        curvatures = []
        for h in hits:
            if h['entity_type'] == 'word_instance':
                c_data = measure_manifold_curvature(h['entity_id'])
                curvatures.append(c_data['curvature'])
                
        if not curvatures:
            return {\"type\": \"FlatType\", \"note\": \"No word resonances found to measure variance.\"}
            
        variance = np.var(curvatures)
        monodromy = \"FlatType\" if variance < 0.1 else \"TwistedType\"
        
        return {
            "entry_address": address,
            "monodromy_type": monodromy,
            "curvature_variance": round(float(variance), 4),
            "sample_count": len(curvatures)
        }

        @mcp.tool()
        def resolve_research_completeness(addresses: list[str]) -> dict:
        \"\"\"Apply UOR Index Theorem to determine if a research set is complete (P3.4, P3.6).

        Calculates the topological gap and suggests specific actions to reach completeness.
        \"\"\"
        from src.utils.topology import compute_uor_index
        from src.db import get_connection
        conn = get_connection()

        idx_data = compute_uor_index(conn, addresses)

        suggestions = []
        if not idx_data['is_complete']:
            if idx_data['betti_numbers']['beta_1'] > 0:
                suggestions.append(\"Redundant constraints detected (Cycles). Try merging similar interpretations.\")
            if idx_data['euler_characteristic'] < len(addresses):
                suggestions.append(\"Incompatible manifold islands. Look for bridging lemmas or roots to connect these nodes.\")
            if idx_data['uor_index'] > 0.5:
                suggestions.append(\"High residual entropy. Hypothesis requires more granular feature analysis (Gauge refinement).\")

        return {
            "metrics": idx_data,
            "status": "COMPLETE" if idx_data['is_complete'] else "INCOMPLETE",
            "refinement_suggestions": suggestions
        }

        @mcp.tool()
        def measure_verification_convergence(entry_address: str) -> dict:
        \"\"\"Track verification progress as a spectral convergence sequence (P3.8).

        Shows how close an interpretation is to full verification across its 
        entire resonance field.
        \"\"\"
        conn = get_connection()
        row = conn.execute(\"SELECT anchor_type, anchor_ids, content FROM holonomic_entries WHERE address = ?\", (entry_address,)).fetchone()
        if not row:
            return {\"error\": \"Entry not found\"}

        anchor_type = row['anchor_type']
        anchor_ids = row['anchor_ids']

        # 1. Find total resonances
        from src.utils.addressing import find_by_address, get_address
        anchor_addr = get_address(conn, anchor_type, str(anchor_ids))
        hits = find_by_address(conn, anchor_addr)
        total_instances = len([h for h in hits if h['entity_type'] == 'word_instance'])

        if total_instances == 0:
            return {\"convergence\": 1.0, \"note\": \"Unanchored claim is vacuously converged.\"}

        # 2. Find verified resonances
        # (Looking for other holonomic_entries with same content/anchor but verified status)
        # This is a simplified proxy for P3.8 completion
        verified_count = conn.execute(\"\"\"
            SELECT COUNT(*) FROM holonomic_entries 
            WHERE content = ? AND anchor_type = ? AND verification = 'supports'
        \"\"\", (row['content'], anchor_type)).fetchone()[0]

        convergence = min(verified_count / total_instances, 1.0)

        # 3. Spectral Gap (Proxy)
        # λ_1 bounds convergence rate. We model it as the diversity of the unverified field.
        lambda_1 = 1.0 - convergence

        return {
            \"entry_address\": entry_address,
            \"total_instances_in_field\": total_instances,
            \"verified_instances\": verified_count,
            \"convergence_ratio\": round(convergence, 4),
            \"spectral_gap\": round(lambda_1, 4),
            \"note\": \"Convergence approaches 1.0 as every resonance in the manifold is checked.\"
        }
        Applied fuzzy match at line 158-163.


