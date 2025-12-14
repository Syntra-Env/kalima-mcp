#!/usr/bin/env python3
"""
Verify that tokens match the original verse text.
Compares normalized versions to account for compound words and variations.
"""

import sqlite3
import json
from pathlib import Path


def normalize(text):
    """Normalize for comparison - remove all whitespace."""
    return text.replace(' ', '').replace('\u200c', '').replace('\u200d', '')


def verify_all_verses(db_path):
    """Check that tokens match verse texts."""
    print(f"Opening database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Fetching all verses...")
    verses = cursor.execute('''
        SELECT surah_number, ayah_number, text
        FROM verse_texts
        ORDER BY surah_number, ayah_number
    ''').fetchall()

    mismatches = []
    perfect_matches = 0
    compound_matches = 0

    for surah, ayah, verse_text in verses:
        # Get tokens
        tokens = cursor.execute('''
            SELECT text
            FROM tokens
            WHERE verse_surah = ? AND verse_ayah = ?
            ORDER BY token_index
        ''', (surah, ayah)).fetchall()

        if not tokens:
            mismatches.append({
                'ref': f'{surah}:{ayah}',
                'issue': 'No tokens found',
                'verse_text': verse_text
            })
            continue

        token_texts = [t[0] for t in tokens]
        joined_tokens = ' '.join(token_texts)

        # Check exact match first
        if joined_tokens == verse_text:
            perfect_matches += 1
            continue

        # Check normalized match (for compound words, Bismillah, etc.)
        verse_normalized = normalize(verse_text)
        tokens_normalized = normalize(joined_tokens)

        if verse_normalized == tokens_normalized:
            compound_matches += 1
            continue

        # Mismatch found
        mismatches.append({
            'ref': f'{surah}:{ayah}',
            'verse_text': verse_text,
            'joined_tokens': joined_tokens,
            'verse_normalized': verse_normalized,
            'tokens_normalized': tokens_normalized,
            'length_diff': len(verse_normalized) - len(tokens_normalized)
        })

        if (surah * 1000 + ayah) % 500 == 0:
            print(f"Checked {surah}:{ayah}...")

    conn.close()

    # Report results
    print("\n" + "=" * 60)
    print("VERIFICATION RESULTS")
    print("=" * 60)
    print(f"Total verses: {len(verses)}")
    print(f"Perfect matches: {perfect_matches}")
    print(f"Compound word matches (normalized): {compound_matches}")
    print(f"Mismatches: {len(mismatches)}")

    if mismatches:
        print("\n" + "=" * 60)
        print("MISMATCHES FOUND")
        print("=" * 60)

        # Save detailed mismatches to file
        with open('temp_token_mismatches.json', 'w', encoding='utf-8') as f:
            json.dump(mismatches, f, ensure_ascii=False, indent=2)

        print(f"\nFirst 10 mismatches:")
        for mismatch in mismatches[:10]:
            print(f"\n{mismatch['ref']}:")
            print(f"  Issue: {mismatch.get('issue', 'Text mismatch')}")
            if 'length_diff' in mismatch:
                print(f"  Length diff: {mismatch['length_diff']} chars")

        print(f"\nFull details saved to: temp_token_mismatches.json")
    else:
        print("\nAll tokens match verse texts! ✓")

    return len(mismatches) == 0


if __name__ == "__main__":
    db_path = Path(__file__).parent.parent / "data" / "database" / "kalima.db"

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        exit(1)

    success = verify_all_verses(db_path)
    exit(0 if success else 1)
