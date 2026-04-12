#!/usr/bin/env python3
"""Reload roots - use correct matching"""
import sqlite3
from pathlib import Path
import re
import sys

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
KALIMA_DB = DATA_DIR / "kalima.db"
MORPH_FILE = DATA_DIR / "quran-morphology.txt"

# Full Buckwalter to Arabic mapping
BUCKWALTER_MAP = str.maketrans({
    '3': '\u0621',  # ع (Aa)
    '2': '\u0621',  # ء (Aa)
    'a': '\u0627',  # ا
    'b': '\u0628',  # ب
    't': '\u062a',  # ت
    'v': '\u062a',  # ة
    'g': '\u063a',  # غ
    'd': '\u062f',  # د
    'D': '\u0636',  # ض
    'r': '\u0631',  # ر
    'z': '\u0632',  # ز
    's': '\u0633',  # س
    'S': '\u0634',  # ش
    'c': '\u0635',  # ص
    '.': '\u0641',  # ف
    'q': '\u0642',  # ق
    'k': '\u0643',  # ك
    'l': '\u0644',  # ل
    'm': '\u0645',  # م
    'n': '\u0646',  # ن
    'h': '\u0647',  # ه
    'w': '\u0648',  # و
    'y': '\u064a',  # ي
    'A': '\u0623',  # أ
    'u': '\u0624',  # ؤ
    'i': '\u0626',  # ي (hamza)
    'p': '\u0629',  # ة
    'J': '\u062c',  # ج
    'H': '\u062d',  # ح
    'X': '\u062e',  # خ
    'G': '\u063a',  # غ
    'O': '\u0626',  # ؾ
    'E': '\u0639',  # ع
    'F': '\u0641',  # ف
    'K': '\u0643',  # ك
    'L': '\u0644',  # ل
    'M': '\u0645',  # م
    'N': '\u0646',  # ن
    'Y': '\u064a',  # ي
    ' ': ' '
})

def buckwalter_to_arabic(root):
    """Convert Buckwalter to Arabic"""
    result = []
    for c in root:
        result.append(BUCKWALTER_MAP.get(c, c))
    return ''.join(result)

def arabic_to_buckwalter(root):
    """Convert Arabic to Buckwalter"""
    rev = {v: k for k, v in BUCKWALTER_MAP.items()}
    result = []
    for c in root:
        result.append(rev.get(c, c))
    return ''.join(result)

def main():
    conn = sqlite3.connect(str(KALIMA_DB))
    cursor = conn.cursor()
    
    # Check current state
    cursor.execute("SELECT COUNT(*) FROM morpheme_types WHERE root_id IS NOT NULL")
    current = cursor.fetchone()[0]
    print(f"Current words with roots: {current}")
    
    if current > 0:
        print("Already have roots, stopping")
        return
    
    # Get all roots from features (in Buckwalter)
    cursor.execute("SELECT id, lookup_key FROM features WHERE feature_type = 'root'")
    roots_in_db = {row[1]: row[0] for row in cursor.fetchall()}
    print(f"Roots in features: {len(roots_in_db)}")
    
    # Add any missing Arabic roots to features
    print("\nChecking for missing Arabic roots...")
    
    # Load morphology and extract roots
    morph_roots = set()
    with open(MORPH_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if 'ROOT:' not in line:
                continue
            # Extract root from ROOT:xxx
            match = re.search(r'ROOT:(\w+)', line)
            if match:
                root_bw = match.group(1)
                morph_roots.add(root_bw)
    
    print(f"Unique roots in morphology: {len(morph_roots)}")
    
    # Find missing
    missing = morph_roots - set(roots_in_db.keys())
    print(f"Missing from features: {len(missing)}")
    
    # Add missing
    for root in missing:
        cursor.execute(
            "INSERT INTO features (feature_type, category, lookup_key) VALUES (?, ?, ?)",
            ('root', None, root)
        )
    
    if missing:
        conn.commit()
        print(f"Added {len(missing)} roots")
    
    # Rebuild lookup
    cursor.execute("SELECT id, lookup_key FROM features WHERE feature_type = 'root'")
    root_lookup = {row[1]: row[0] for row in cursor.fetchall()}
    print(f"Total roots: {len(root_lookup)}")
    
    # Load word instances mapping
    cursor.execute("SELECT verse_surah, verse_ayah, word_index, word_type_id FROM word_instances")
    loc_to_wtid = {(s, a, w): t for s, a, w, t in cursor.fetchall()}
    print(f"Word instances: {len(loc_to_wtid)}")
    
    # Parse and update
    print("\nUpdating roots...")
    updated = 0
    with open(MORPH_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if 'ROOT:' not in line:
                continue
            
            match = re.search(r'ROOT:(\w+)', line)
            root = match.group(1)  # This is Buckwalter like "3laq"
            
            parts = line.strip().split('\t')
            if len(parts) < 2:
                continue
            
            try:
                surah, ayah, word = map(int, parts[0].split(':'))
                word -= 1  # Convert to 0-based
            except:
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
    print(f"Updated {updated} words")
    
    # Final
    cursor.execute("SELECT COUNT(*) FROM morpheme_types WHERE root_id IS NOT NULL")
    final_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM morpheme_types")
    total = cursor.fetchone()[0]
    
    print(f"\nFinal: {final_count}/{total} ({100*final_count//total}%)")
    
    # Check specific root
    root_id = root_lookup.get('3laq')  # Buckwalter for علق
    if root_id:
        cursor.execute("""
            SELECT wi.verse_surah, wi.verse_ayah
            FROM word_instances wi
            JOIN morpheme_types mt ON wi.word_type_id = mt.id
            WHERE mt.root_id = ?
        """, (root_id,))
        rows = cursor.fetchall()
        print(f"\nRoot 3laq (علق): {len(rows)} instances")
        for r in rows[:10]:
            print(f"  {r[0]}:{r[1]}")
    
    conn.close()

if __name__ == "__main__":
    main()