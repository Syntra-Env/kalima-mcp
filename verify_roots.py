#!/usr/bin/env python3
"""Compare root accuracy between sources"""
import sqlite3
from pathlib import Path
import re
from collections import Counter

QUL_DB = Path(__file__).resolve().parent.parent / "data" / "ayah-root.db" / "ayah-root.db"
MORPH_FILE = Path(__file__).resolve().parent.parent / "data" / "quran-morphology.txt"
# Adjust path - script is in scripts/ folder
if not MORPH_FILE.exists():
    MORPH_FILE = Path(__file__).resolve().parent / "data" / "quran-morphology.txt"
KALIMA_DB = Path(__file__).resolve().parent.parent / "data" / "kalima.db"

def load_morph_roots():
    """Load roots from quran-morphology.txt"""
    roots = {}
    if not MORPH_FILE.exists():
        print(f"Morphology file not found: {MORPH_FILE}")
        return roots
    with open(MORPH_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) < 2:
                continue
            loc = parts[0]
            match = re.search(r'ROOT:(\w+)', line)
            if match:
                root = match.group(1)
                surah, ayah, word = loc.split(':')
                key = f"{surah}:{ayah}"
                if key not in roots:
                    roots[key] = []
                roots[key].append(root)
    return roots

def load_qul_roots():
    """Load roots from Tarteel QUL"""
    conn = sqlite3.connect(str(QUL_DB))
    roots = {}
    for row in conn.execute("SELECT verse_key, text FROM roots").fetchall():
        surah, ayah = row[0].split(':')
        key = f"{surah}:{ayah}"
        roots[key] = row[1].split()
    return roots

def load_kalima_roots():
    """Load roots from kalima.db word instances"""
    conn = sqlite3.connect(str(KALIMA_DB))
    roots = {}
    cursor = conn.execute("""
        SELECT wi.verse_surah, wi.verse_ayah, f.lookup_key
        FROM word_instances wi
        JOIN morpheme_types mt ON wi.word_type_id = mt.id
        JOIN features f ON mt.root_id = f.id
        WHERE f.feature_type = 'root'
    """)
    for surah, ayah, root in cursor.fetchall():
        key = f"{surah}:{ayah}"
        if key not in roots:
            roots[key] = []
        roots[key].append(root)
    return roots

def main():
    print("Loading roots from sources...")
    morph = load_morph_roots()
    qul = load_qul_roots()
    kalima = load_kalima_roots()
    
    print(f"Morphology: {sum(len(v) for v in morph.values())} root-words across {len(morph)} verses")
    print(f"QUL: {sum(len(v) for v in qul.values())} root-words across {len(qul)} verses")
    print(f"Kalima: {sum(len(v) for v in kalima.values())} root-words across {len(kalima)} verses")
    
    # Compare verse by verse
    print("\n=== Comparing per-verse root sets ===")
    
    all_verses = set(morph.keys()) | set(qul.keys()) | set(kalima.keys())
    
    mismatches = []
    matches = []
    
    for verse in sorted(all_verses, key=lambda x: (int(x.split(':')[0]), int(x.split(':')[1]))):
        m_roots = set(morph.get(verse, []))
        q_roots = set(qul.get(verse, []))
        k_roots = set(kalima.get(verse, []))
        
        # Check if Kalima matches QUL (most complete source)
        if k_roots != q_roots:
            mismatches.append((
                verse, 
                len(m_roots), len(q_roots), len(k_roots),
                m_roots, q_roots, k_roots
            ))
        else:
            matches.append(verse)
    
    print(f"\nMatching verses (Kalima == QUL): {len(matches)}/{len(all_verses)}")
    print(f"Mismatched verses: {len(mismatches)}")
    
    # Show some mismatches
    print("\nFirst 10 mismatches:")
    for v, mc, qc, kc, m_r, q_r, k_r in mismatches[:10]:
        if k_r != q_r:
            print(f"\n{v}:")
            print(f"  Morph: {mc} roots - {list(m_r)[:5]}")
            print(f"  QUL:   {qc} roots - {list(q_r)[:5]}")
            print(f"  Kal:   {kc} roots - {list(k_r)[:5]}")
            # Show differences
            only_q = q_r - k_r
            only_k = k_r - q_r
            if only_q:
                print(f"  Only in QUL: {list(only_q)[:5]}")
            if only_k:
                print(f"  Only in Kal: {list(only_k)[:5]}")

if __name__ == "__main__":
    main()