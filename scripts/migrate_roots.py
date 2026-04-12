#!/usr/bin/env python3
"""Migrate missing roots from quran-morphology.txt to kalima.db"""
import sqlite3
from pathlib import Path
import re

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"
MORPH_PATH = Path(__file__).resolve().parent.parent / "data" / "quran-morphology.txt"

def parse_root(line):
    """Extract ROOT:xxx from morphology line"""
    match = re.search(r'ROOT:(\w+)', line)
    return match.group(1) if match else None

def parse_location(loc):
    """Parse 'surah:ayah:word:part' to (surah, ayah, word_index)"""
    parts = loc.split(':')
    return int(parts[0]), int(parts[1]), int(parts[2]) - 1  # 0-index word

def main():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Build mapping: (surah, ayah, word_index) -> word_type_id
    print("Building word location index...")
    cursor.execute("""
        SELECT verse_surah, verse_ayah, word_index, word_type_id
        FROM word_instances
    """)
    loc_to_wtid = {}
    for surah, ayah, word_idx, wtid in cursor.fetchall():
        loc_to_wtid[(surah, ayah, word_idx)] = wtid

    print(f"Indexed {len(loc_to_wtid)} word instances")

    # Load roots from morphology file
    print("Loading roots from quran-morphology.txt...")
    root_updates = set()
    with open(MORPH_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or 'ROOT:' not in line:
                continue
            
            parts = line.split('\t')
            if len(parts) < 2:
                continue
            
            loc = parts[0]
            root = parse_root(line)
            
            try:
                surah, ayah, word_idx = parse_location(loc)
            except:
                continue
            
            key = (surah, ayah, word_idx)
            if key in loc_to_wtid:
                root_updates.add((root, loc_to_wtid[key]))

    print(f"Found {len(root_updates)} words with roots in morphology file")

    # Get existing roots from features table
    print("Loading existing roots...")
    cursor.execute("SELECT id, lookup_key FROM features WHERE feature_type = 'root'")
    existing_roots = {row[1] for row in cursor.fetchall()}
    print(f"Existing roots in features: {len(existing_roots)}")

    # Find missing roots from morphology file
    morphology_roots = {r for r, _ in root_updates}
    missing_roots = morphology_roots - existing_roots
    print(f"Missing roots to add: {len(missing_roots)}")

    # Add missing roots to features table
    if missing_roots:
        print("Adding missing roots to features table...")
        cursor.executemany(
            "INSERT OR IGNORE INTO features (feature_type, category, lookup_key) VALUES (?, ?, ?)",
            [('root', None, r) for r in missing_roots]
        )
        conn.commit()
        print(f"Added {len(missing_roots)} roots")

    # Rebuild root lookup
    cursor.execute("SELECT id, lookup_key FROM features WHERE feature_type = 'root'")
    root_id_lookup = {row[1]: row[0] for row in cursor.fetchall()}
    print(f"Total roots in features: {len(root_id_lookup)}")

    # Apply updates
    print("Updating morpheme_types root_id...")
    updated = 0
    not_found = 0
    for root_str, wtid in root_updates:
        root_id = root_id_lookup.get(root_str)
        if root_id:
            cursor.execute(
                "UPDATE morpheme_types SET root_id = ? WHERE id = ?",
                (root_id, wtid)
            )
            updated += 1
        else:
            not_found += 1
    
    conn.commit()
    print(f"Updated {updated} root mappings")
    if not_found:
        print(f"Still not found: {not_found}")

    # Show results
    cursor.execute("""
        SELECT COUNT(*) FROM morpheme_types WHERE root_id IS NOT NULL
    """)
    with_root = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM morpheme_types")
    total = cursor.fetchone()[0]
    
    print(f"\nResults:")
    print(f"  With root_id: {with_root}/{total} ({100*with_root//total}%)")

    # Check 4:129 now
    print("\nChecking 4:129...")
    cursor.execute("""
        SELECT wi.word_type_id, mt.uthmani_text, f.lookup_key
        FROM word_instances wi
        JOIN morpheme_types mt ON wi.word_type_id = mt.id
        LEFT JOIN features f ON mt.root_id = f.id
        WHERE wi.verse_surah = 4 AND wi.verse_ayah = 129 AND wi.word_index = 14
    """)
    row = cursor.fetchone()
    if row:
        print(f"  Word 14: {row[1]} -> root: {row[2]}")
    
    # Check علق root instances
    print("\nVerifying root علق (3alaqah)...")
    cursor.execute("""
        SELECT wi.verse_surah, wi.verse_ayah, mt.uthmani_text, f.lookup_key
        FROM word_instances wi
        JOIN morpheme_types mt ON wi.word_type_id = mt.id
        JOIN features f ON mt.root_id = f.id
        WHERE f.lookup_key = 'علق'
        ORDER BY wi.verse_surah, wi.verse_ayah
    """)
    rows = cursor.fetchall()
    for r in rows:
        print(f"  {r[0]}:{r[1]} - {r[2]}")
    print(f"  Total: {len(rows)} instances")
    
    conn.close()

if __name__ == "__main__":
    main()