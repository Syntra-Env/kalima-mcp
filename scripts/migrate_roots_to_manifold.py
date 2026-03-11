import sqlite3
import hashlib
import sys
import os

# Ensure we can import from src
sys.path.append(os.getcwd())
from src.db import get_connection, save_database

def compute_root_address(lookup_key: str) -> str:
    """Canonical address for a root: SHA256('root:' + lookup_key)."""
    canonical = f"root:{lookup_key}".encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()

def migrate_roots():
    conn = get_connection()
    
    print("[*] Fetching legacy roots...")
    roots = conn.execute(
        "SELECT id, lookup_key FROM features WHERE feature_type='root'"
    ).fetchall()
    
    print(f"[*] Found {len(roots)} roots to migrate.")
    
    count = 0
    for r in roots:
        root_id = r['id']
        key = r['lookup_key']
        
        # specific fix for potential null keys
        if not key:
            print(f"[!] Skipping root ID {root_id} (no lookup_key)")
            continue
            
        address = compute_root_address(key)
        
        # Insert into content_addresses
        conn.execute(
            """INSERT OR REPLACE INTO content_addresses (entity_type, entity_id, address)
               VALUES (?, ?, ?)""",
            ('root', str(root_id), address)
        )
        count += 1
        
        if count % 100 == 0:
            print(f"    Migrated {count}...")
            
    save_database()
    print(f"[+] Migration complete. {count} roots added to the manifold.")

if __name__ == "__main__":
    migrate_roots()
