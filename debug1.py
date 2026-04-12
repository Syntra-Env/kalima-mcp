#!/usr/bin/env python3
"""Debug - just count"""
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
kalima_db = DATA_DIR / "kalima.db"
qul_db = DATA_DIR / "ayah-root.db" / "ayah-root.db"

kalima = sqlite3.connect(str(kalima_db))
qul = sqlite3.connect(str(qul_db))

# Get QUL roots for verse 1:1
q_text = qul.execute("SELECT text FROM roots WHERE verse_key = '1:1'").fetchone()[0]
q_set = set(q_text.split())

# Get Kalima roots for verse 1:1
k_roots = set()
for root, in kalima.execute("""
    SELECT f.lookup_key
    FROM word_instances wi
    JOIN morpheme_types mt ON wi.word_type_id = mt.id
    JOIN features f ON mt.root_id = f.id
    WHERE f.feature_type = 'root' AND wi.verse_surah = 1 AND wi.verse_ayah = 1
""").fetchall():
    k_roots.add(root)

print(f"QUL count: {len(q_set)}")
print(f"Kalima count: {len(k_roots)}")

if q_set == k_roots:
    print("MATCH!")
else:
    # Find differences
    diff = q_set ^ k_roots  # symmetric difference
    print(f"Difference: {len(diff)}")
    
    # Get IDs to show (avoid Arabic in output)
    only_qul = q_set - k_roots
    only_kal = k_roots - q_set
    
    # Lookup ID for each to verify
    if only_qul:
        for r in list(only_qul)[:3]:
            row = kalima.execute("SELECT id FROM features WHERE lookup_key = ?", (r,)).fetchone()
            print(f"  Only QUL: {r} (id={row[0] if row else 'N/A'})")
    
    if only_kal:
        for r in list(only_kal)[:3]:
            row = kalima.execute("SELECT id FROM features WHERE lookup_key = ?", (r,)).fetchone()
            print(f"  Only Kal: {r} (id={row[0] if row else 'N/A'})")

kalima.close()
qul.close()