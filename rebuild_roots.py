#!/usr/bin/env python3
"""Rebuild root_id fromVerified sources only"""
import sqlite3
from pathlib import Path
import re
from collections import defaultdict

MORPH_FILE = Path(__file__).resolve().parent / "data" / "quran-morphology.txt"
KALIMA_DB = Path(__file__).resolve().parent / "data" / "kalima.db"

def main():
    print("Loading morpheme_types with roots...")
    conn = sqlite3.connect(str(KALIMA_DB))
    
    # Count by source
    cursor = conn.cursor()
    
    # Get roots that came from morphology file (can verify by position)
    # and remove everything else
    print("Counting current state...")
    cursor.execute("""
        SELECT COUNT(*) FROM morpheme_types WHERE root_id IS NOT NULL
    """)
    with_root = cursor.fetchone()[0]
    print(f"Currently with root: {with_root}")
    
    # Reset ALL roots
    print("\nResetting all roots to NULL...")
    cursor.execute("UPDATE morpheme_types SET root_id = NULL")
    conn.commit()
    
    # Now rebuild using quran-morphology.txt which has exact position info
    print("\nRebuilding from quran-morphology.txt...")
    
    # Build location -> word_type_id mapping
    cursor.execute("""
        SELECT verse_surah, verse_ayah, word_index, word_type_id
        FROM word_instances
    """)
    loc_to_wtid = {}
    for surah, ayah, widx, wtid in cursor.fetchall():
        loc_to_wtid[(surah, ayah, widx)] = wtid
    
    # Get word_type_id -> uthmani_text for lookup
    cursor.execute("SELECT id, uthmani_text FROM morpheme_types")
    wtid_to_text = {r[0]: r[1] for r in cursor.fetchall()}
    
    print(f"Indexed {len(loc_to_wtid)} word instances")
    
    # Get feature lookup
    cursor.execute("SELECT id, lookup_key FROM features WHERE feature_type = 'root'")
    root_lookup = {r[1]: r[0] for r in cursor.fetchall()}
    print(f"Roots in features: {len(root_lookup)}")
    
    # Parse morphology file and update
    updated = 0
    with open(MORPH_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            match = re.search(r'ROOT:(\w+)', line)
            if not match:
                continue
            
            root = match.group(1)
            parts = line.strip().split('\t')
            if len(parts) < 2:
                continue
            
            loc = parts[0]
            try:
                surah, ayah, word_idx = map(int, loc.split(':'))
            except:
                continue
            
            word_idx -= 0  # Convert to 0-index
            
            wtid = loc_to_wtid.get((surah, ayah, word_idx))
            if not wtid:
                continue
            
            root_id = root_lookup.get(root)
            if root_id:
                cursor.execute(
                    "UPDATE morpheme_types SET root_id = ? WHERE id = ?",
                    (root_id, wtid)
                )
                updated += 1
    
    conn.commit()
    print(f"Updated {updated} words from quran-morphology.txt")
    
    # Add any remaining missing roots from Tarteel by TEXT matching where unique
    print("\nAdding unique text matches from Tarteel...")
    
    # Get words without roots
    cursor.execute("""
        SELECT id, uthmani_text FROM morpheme_types 
        WHERE root_id IS NULL AND uthmani_text IS NOT NULL
    """)
    missing = cursor.fetchall()
    print(f"Words still missing roots: {len(missing)}")
    
    # Build unique text->root mapping (only where one root)
    cursor.execute("""
        SELECT uthmani_text, root_id, COUNT(*) as cnt
        FROM morpheme_types 
        WHERE root_id IS NOT NULL AND uthmani_text IS NOT NULL
        GROUP BY uthmani_text, root_id
        HAVING cnt = 1
    """)
    unique_text = {}
    for text, root_id, cnt in cursor.fetchall():
        if text not in unique_text:
            unique_text[text] = root_id
    
    print(f"Unique text->root mappings: {len(unique_text)}")
    
    # Update remaining where text matches uniquely
    added = 0
    for mt_id, text in missing:
        if text in unique_text:
            cursor.execute(
                "UPDATE morpheme_types SET root_id = ? WHERE id = ?",
                (unique_text[text], mt_id)
            )
            added += 1
    
    conn.commit()
    print(f"Added {added} unique matches")
    
    # Final stats
    cursor.execute("SELECT COUNT(*) FROM morpheme_types WHERE root_id IS NOT NULL")
    with_root = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM morpheme_types")
    total = cursor.fetchone()[0]
    
    print(f"\nFinal: {with_root}/{total} ({100*with_root//total}%) have root_id")
    
    # Check root علق
    root_id = root_lookup.get('علق')
    if root_id:
        cursor.execute("""
            SELECT wi.verse_surah, wi.verse_ayah
            FROM word_instances wi
            JOIN morpheme_types mt ON wi.word_type_id = mt.id
            WHERE mt.root_id = ?
        """, (root_id,))
        rows = cursor.fetchall()
        print(f"\nRoot علق: {len(rows)} instances")
        for r in rows:
            print(f"  {r[0]}:{r[1]}")
    
    conn.close()

if __name__ == "__main__":
    main()