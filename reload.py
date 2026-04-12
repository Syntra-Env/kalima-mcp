#!/usr/bin/env python3
"""Simple root reload"""
import sqlite3
from pathlib import Path
import re

DATA_DIR = Path(__file__).resolve().parent / "data"
db_path = DATA_DIR / "kalima.db"
morph_path = DATA_DIR / "quran-morphology.txt"

conn = sqlite3.connect(str(db_path))
cursor = conn.cursor()

# Get root lookup
cursor.execute("SELECT id, lookup_key FROM features WHERE feature_type = 'root'")
root_lookup = {k: v for v, k in cursor.fetchall()}
print(f"Roots in DB: {len(root_lookup)}")

# Get word_type_id mapping from word_instances (verse -> words with positions)
cursor.execute("""
    SELECT verse_surah, verse_ayah, word_index, word_type_id 
    FROM word_instances
""")
loc_to_wtid = {(s, a, w): t for s, a, w, t in cursor.fetchall()}
print(f"Word instances: {len(loc_to_wtid)}")

# Parse and update - line format: surah:ayah:word:seg
updated = 0
with open(morph_path, 'r', encoding='utf-8') as f:
    for line in f:
        if 'ROOT:' not in line:
            continue
        
        # Extract root
        match = re.search(r'ROOT:(\w+)', line)
        if not match:
            continue
        root = match.group(1)
        
        # Parse location - format is surah:ayah:word:seg
        parts = line.strip().split('\t')
        if len(parts) < 2:
            continue
            
        try:
            loc = parts[0].split(':')
            surah = int(loc[0])
            ayah = int(loc[1])
            word = int(loc[2]) - 1  # Convert to 0-index
        except (ValueError, IndexError):
            continue
        
        key = (surah, ayah, word)
        wtid = loc_to_wtid.get(key)
        
        if wtid and root in root_lookup:
            cursor.execute(
                "UPDATE morpheme_types SET root_id = ? WHERE id = ?",
                (root_lookup[root], wtid)
            )
            updated += 1

conn.commit()
print(f"Updated: {updated} words")

# Stats
cursor.execute("SELECT COUNT(*) FROM morpheme_types WHERE root_id IS NOT NULL")
print(f"Final with root: {cursor.fetchone()[0]}")

# Check علق root
root_993 = root_lookup.get('علق')
if root_993:
    cursor.execute("""
        SELECT wi.verse_surah, wi.verse_ayah
        FROM word_instances wi
        JOIN morpheme_types mt ON wi.word_type_id = mt.id
        WHERE mt.root_id = ?
    """, (root_993,))
    rows = cursor.fetchall()
    print(f"Root علق: {len(rows)} instances")
    
conn.close()
print("Done!")