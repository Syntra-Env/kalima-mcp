#!/usr/bin/env python3
"""Properly compare - sets not ordered"""
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
kalima_db = DATA_DIR / "kalima.db"
qul_db = DATA_DIR / "ayah-root.db" / "ayah-root.db"

kalima = sqlite3.connect(str(kalima_db))
qul = sqlite3.connect(str(qul_db))

# Get roots per verse from QUL (as SET)
qul_roots = {}
for vk, text in qul.execute("SELECT verse_key, text FROM roots").fetchall():
    surah, ayah = map(int, vk.split(':'))
    qul_roots[(surah, ayah)] = set(text.split())

# Get roots per verse from Kalima (as SET)
kal_roots = {}
for surah, ayah, root in kalima.execute("""
    SELECT wi.verse_surah, wi.verse_ayah, f.lookup_key
    FROM word_instances wi
    JOIN morpheme_types mt ON wi.word_type_id = mt.id
    JOIN features f ON mt.root_id = f.id
    WHERE f.feature_type = 'root'
""").fetchall():
    if (surah, ayah) not in kal_roots:
        kal_roots[(surah, ayah)] = set()
    kal_roots[(surah, ayah)].add(root)

print(f"QUL verses: {len(qul_roots)}")
print(f"Kalima verses: {len(kal_roots)}")

# Compare as SETS (order doesn't matter)
matching = 0
mismatch_count = 0

for key in qul_roots:
    q = qul_roots[key]
    k = kal_roots.get(key, set())
    if q == k:
        matching += 1
    else:
        mismatch_count += 1

print(f"Matching exact sets: {matching}/{len(qul_roots)}")
print(f"Mismatched: {mismatch_count}")

# Total roots comparison
total_qul = sum(len(v) for v in qul_roots.values())
total_kal = sum(len(v) for v in kal_roots.values())
print(f"\nTotal roots in QUL: {total_qul}")
print(f"Total roots in Kalima: {total_kal}")

kalima.close()
qul.close()
print("\nDone!")