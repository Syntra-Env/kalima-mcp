
import os
import sys
import numpy as np
import sqlite3
import io
from datetime import datetime, timezone

# Add parent directory to path to import src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db import get_connection, save_database
from kalima.bridge import build_root_vector_from_db

def adapt_array(arr):
    """
    http://stackoverflow.com/a/31312102/190597
    """
    out = io.BytesIO()
    np.save(out, arr)
    out.seek(0)
    return sqlite3.Binary(out.read())

def convert_array(text):
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out)

def cache_all_roots():
    conn = get_connection()
    
    # 1. Get all root IDs
    roots = conn.execute("SELECT id, lookup_key FROM features WHERE feature_type = 'root'").fetchall()
    total = len(roots)
    print(f"[*] Found {total} roots to fingerprint.")
    
    start_time = datetime.now()
    
    for i, row in enumerate(roots):
        rid = row['id']
        key = row['lookup_key']
        
        if i % 100 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            print(f"[*] Processing {i}/{total} ({key})... {elapsed:.1f}s")
            save_database()
            
        try:
            # Build full distributional profile
            rv = build_root_vector_from_db(conn, rid)
            if not rv:
                continue
                
            # Store in cache
            profile_blob = adapt_array(rv.profile)
            weight = rv.distributional_weight
            
            conn.execute("""
                INSERT OR REPLACE INTO root_vectors (root_id, profile, distributional_weight, last_updated)
                VALUES (?, ?, ?, ?)
            """, (rid, profile_blob, weight, datetime.now(timezone.utc).isoformat()))
            
        except Exception as e:
            print(f"[!] Error processing root {rid} ({key}): {e}")
            
    save_database()
    duration = (datetime.now() - start_time).total_seconds()
    print(f"[+] Fingerprinting complete. {total} roots processed in {duration:.1f}s.")

if __name__ == "__main__":
    cache_all_roots()
