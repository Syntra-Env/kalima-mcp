#!/usr/bin/env python3
"""Properly compare Kalima vs QUL roots"""
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
kalima_db = DATA_DIR / "kalima.db"
qul_db = DATA_DIR / "ayah-root.db" / "ayah-root.db"

kalima = sqlite3.connect(str(kalima_db))
qul = sqlite3.connect(str(qul_db))

# Get roots per verse from QUL
qul_roots = {}
for vk, text in qul.execute("SELECT verse_key, text FROM roots").fetchall():
    surah, ayah = vk.split(':')
    key = (int(surah), int(ayah))
    qul_roots[key] = set(text.split())

# Get roots per verse from Kalima
kal_roots = {}
for surah, ayah, root in kalima.execute("""
    SELECT wi.verse_surah, wi.verse_ayah, f.lookup_key
    FROM word_instances wi
    JOIN morpheme_types mt ON wi.word_type_id = mt.id
    JOIN features f ON mt.root_id = f.id
    WHERE f.feature_type = 'root'
""").fetchall():
    key = (surah, ayah)
    if key not in kal_roots:
        kal_roots[key] = set()
    kal_roots[key].add(root)

print(f"QUL verses: {len(qul_roots)}")
print(f"Kalima verses: {len(kal_roots)}")

# Compare counts
matching_count = 0
matching = []
mismatched = []

for key in qul_roots:
    q = qul_roots.get(key, set())
    k = kal_roots.get(key, set())
    if q == k:
        matching_count += 1
        matching.append(key)
    else:
        mismatched.append((key, len(q), len(k), q, k))

print(f"Matching: {matching_count}/{len(qul_roots)}")

if mismatched:
    print(f"\nTotal mismatched: {len(mismatched)}")
    print("\nFirst 5 mismatches:")
    for key, qc, kc, q, k in mismatched[:5]:
        print(f"  {key[0]}:{key[1]} - QUL: {qc}, Kal: {kc}")
        if q - k:
            print(f"    Only in QUL: {list(q - k)[:5]}")
        if k - q:
            print(f"    Only in Kal: {list(k - q)[:5]}")

kalima.close()
qul.close()
print("\nDone!")