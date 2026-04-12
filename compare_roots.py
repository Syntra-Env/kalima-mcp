#!/usr/bin/env python3
"""Analyze root mismatches - simpler version"""
import sqlite3
from pathlib import Path

QUL_DB = Path(__file__).resolve().parent / "data" / "ayah-root.db" / "ayah-root.db"
KALIMA_DB = Path(__file__).resolve().parent / "data" / "kalima.db"

def main():
    qul_conn = sqlite3.connect(str(QUL_DB))
    kalima_conn = sqlite3.connect(str(KALIMA_DB))
    
    # Get root count per verse
    qul_counts = {}
    for vk, text in qul_conn.execute("SELECT verse_key, text FROM roots").fetchall():
        qul_counts[vk] = len(text.split())
    
    kalima_counts = {}
    for surah, ayah, root in kalima_conn.execute("""
        SELECT wi.verse_surah, wi.verse_ayah, f.lookup_key
        FROM word_instances wi
        JOIN morpheme_types mt ON wi.word_type_id = mt.id
        JOIN features f ON mt.root_id = f.id
        WHERE f.feature_type = 'root'
    """).fetchall():
        key = f"{surah}:{ayah}"
        kalima_counts[key] = kalima_counts.get(key, 0) + 1
    
    print(f"QUL verses: {len(qul_counts)}")
    print(f"Kalima verses with roots: {len(kalima_counts)}")
    
    # Compare counts
    differences = []
    for vk in qul_counts:
        qc = qul_counts[vk]
        kc = kalima_counts.get(vk, 0)
        if qc != kc:
            differences.append((vk, qc, kc))
    
    print(f"\nVerses with different root counts: {len(differences)}")
    
    # Sort by difference magnitude
    differences.sort(key=lambda x: abs(x[1] - x[2]), reverse=True)
    
    print("\nTop 10 largest differences (QUL vs Kal):")
    for vk, qc, kc in differences[:10]:
        print(f"  {vk}: QUL={qc}, Kal={kc}, diff={qc-kc}")
    
    # Total roots comparison
    total_qul = sum(qul_counts.values())
    total_kalima = sum(kalima_counts.values())
    
    print(f"\nTotal root occurrences:")
    print(f"  QUL: {total_qul}")
    print(f"  Kalima: {total_kalima}")
    print(f"  Difference: {total_kalima - total_qul}")
    
    qul_conn.close()
    kalima_conn.close()

if __name__ == "__main__":
    main()