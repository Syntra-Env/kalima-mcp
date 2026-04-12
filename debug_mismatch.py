#!/usr/bin/env python3
"""Find mismatches in detail"""
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
kalima_db = DATA_DIR / "kalima.db"
qul_db = DATA_DIR / "ayah-root.db" / "ayah-root.db"

kalima = sqlite3.connect(str(kalima_db))
qul = sqlite3.connect(str(qul_db))

# Get roots from QUL for verse 2:282 which was very different
q_text = qul.execute("SELECT text FROM roots WHERE verse_key = '2:282'").fetchone()[0]
q_roots = set(q_text.split())
print("2:282 in QUL:")
print(f"  Roots: {q_text[:100]}...")
print(f"  Count: {len(q_roots)}")

# Get roots from Kalima
k_roots = set()
for root in kalima.execute("""
    SELECT f.lookup_key
    FROM word_instances wi
    JOIN morpheme_types mt ON wi.word_type_id = mt.id
    JOIN features f ON mt.root_id = f.id
    WHERE f.feature_type = 'root' AND wi.verse_surah = 2 AND wi.verse_ayah = 282
""").fetchall():
    k_roots.add(root[0])

print(f"\n2:282 in Kalima:")
print(f"  Roots: {list(k_roots)[:10]}...")
print(f"  Count: {len(k_roots)}")

print(f"\nMatching: {len(q_roots & k_roots)}")
print(f"Only QUL: {len(q_roots - k_roots)}")
print(f"Only Kalima: {len(k_roots - q_roots)}")

# Show some only in QUL
only_qul = q_roots - k_roots
if only_qul:
    print(f"\nOnly in QUL (first 10): {list(only_qul)[:10]}")

# Show some only in Kalima
only_kal = k_roots - q_roots
if only_kal:
    print(f"Only in Kalima (first 10): {list(only_kal)[:10]}")

kalima.close()
qul.close()