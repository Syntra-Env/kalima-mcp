import sqlite3
import hashlib
from datetime import datetime, timezone
import sys
import os

# Ensure we can import from src
sys.path.append(os.getcwd())
from src.db import get_connection, save_database

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def dock_research_claim(content, anchor_address, category="general", phase="validation"):
    if not anchor_address:
        print(f"[!] Skipping claim: {content[:30]}... (No anchor address)")
        return

    conn = get_connection()
    
    # 1. Compute entry address: (Content | Anchor_Address)
    canonical = content.encode('utf-8') + b'|' + anchor_address.encode('ascii')
    entry_addr = hashlib.sha256(canonical).hexdigest()
    
    # 2. Get anchor info
    row = conn.execute("SELECT entity_type, entity_id FROM content_addresses WHERE address=?", (anchor_address,)).fetchone()
    anchor_type = row['entity_type'] if row else 'unknown'
    anchor_id = row['entity_id'] if row else 'unknown'

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
    print(f"[+] Docked Claim: {entry_addr[:10]}... to {anchor_type}:{anchor_id} ({anchor_address[:10]}...)")

# --- Get Addresses ---
conn = get_connection()
def get_addr(e_type, e_id):
    r = conn.execute("SELECT address FROM content_addresses WHERE entity_type=? AND entity_id=?", (e_type, str(e_id))).fetchone()
    return r[0] if r else None

def get_root_addr(lookup_key):
    r = conn.execute("SELECT id FROM features WHERE lookup_key=?", (lookup_key,)).fetchone()
    if r:
        return get_addr('root', r['id'])
    return None

# Addresses
verse_12_31 = get_addr('verse', '12:31')
verse_44_20 = get_addr('verse', '44:20')
root_bashar = get_root_addr('بشر')
root_melek = get_root_addr('ملك')
root_sfk = get_root_addr('سفك') # Safaka

# Claims
claims = [
    # Verse Anchors
    {
        "content": "Bashar (broadcaster) vs Melek (governor/disciplined). Bashar refers to indiscriminate broadcasting of information. Melek refers to those who are disciplined and selective in disclosing information (Information Governance).",
        "anchor": verse_12_31, 
        "category": "linguistic"
    },
    {
        "content": "Monodromy and Ambiguity: In 44:20, the figure (Isa) confesses to using ambiguous language ('Rabbi wa Rabbikum') to avoid being cast away. This created a 'twisted' holonomy allowing followers to project their own meanings (shirk).",
        "anchor": verse_44_20, 
        "category": "interpretation"
    },
    
    # Root Anchors (New!)
    {
        "content": "Root Definition: B-Sh-R implies 'skin' or 'surface broadcasting'. A Bashar transmits information outward indiscriminately (like a loose cannon).",
        "anchor": root_bashar,
        "category": "lexical"
    },
    {
        "content": "Root Definition: M-L-K implies 'ownership/control/governance'. A Melek is one who exercises disciplined governance over information disclosure.",
        "anchor": root_melek,
        "category": "lexical"
    },
     {
        "content": "Root Definition: S-F-K implies 'talking a lot' or 'over-disclosing', distinct from the traditional 'shedding blood'. It relates to the unchecked flow of critical knowledge (Dima).",
        "anchor": root_sfk,
        "category": "lexical"
    }
]

for c in claims:
    dock_research_claim(c['content'], c['anchor'], c['category'])
