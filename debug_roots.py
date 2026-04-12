#!/usr/bin/env python3
"""Debug root loading"""
import sqlite3
from pathlib import Path
import re

DATA_DIR = Path(__file__).resolve().parent / "data"
KALIMA_DB = DATA_DIR / "kalima.db"
MORPH_FILE = DATA_DIR / "quran-morphology.txt"

def main():
    conn = sqlite3.connect(str(KALIMA_DB))
    cursor = conn.cursor()
    
    # Get some locations from word_instances
    cursor.execute("SELECT verse_surah, verse_ayah, word_index, word_type_id FROM word_instances LIMIT 5")
    print("Sample word_instances:")
    for row in cursor.fetchall():
        print(f"  {row}")
    
    # Get locations from morphology file
    print("\nSample morphology lines:")
    with open(MORPH_FILE, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i > 5:
                break
            print(f"  {line.strip()}")
    
    # Check if there's a mapping issue
    # Morphology has: surah:ayah:word:part (e.g., 4:129:14:3)
    # Word_instances has: word_index 0-based
    
    print("\nChecking one root update...")
    
    # Test line 20923 which has root علق
    cursor.execute("SELECT id, lookup_key FROM features WHERE feature_type='root' AND lookup_key = 'علق'")
    row = cursor.fetchone()
    if row:
        print(f"Root found in features: id={row[0]}, key={row[1]}")
    else:
        print("Root not found!")
    
    conn.close()

if __name__ == "__main__":
    main()