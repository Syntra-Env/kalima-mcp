#!/usr/bin/env python3
"""
Simple script: Replace tokens table text with fully-vocalized verse_texts split.
Assumes tokens are already correctly aligned with space-split verse text.
"""

import sqlite3
import sys
from pathlib import Path


def fix_tokens(db_path):
    """Update all tokens with full diacritics from verse_texts."""
    print(f"Opening database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("Fetching verses...")
    verses = cursor.execute('''
        SELECT surah_number, ayah_number, text
        FROM verse_texts
        ORDER BY surah_number, ayah_number
    ''').fetchall()

    updated = 0
    skipped = 0

    for surah, ayah, verse_text in verses:
        # Split verse on spaces
        full_tokens = verse_text.strip().split()

        # Get DB tokens
        db_tokens = cursor.execute('''
            SELECT id, token_index
            FROM tokens
            WHERE verse_surah = ? AND verse_ayah = ?
            ORDER BY token_index
        ''', (surah, ayah)).fetchall()

        if len(db_tokens) != len(full_tokens):
            print(f"SKIP {surah}:{ayah} - count mismatch: {len(db_tokens)} vs {len(full_tokens)}")
            skipped += 1
            continue

        # Update each token
        for (token_id, _), new_text in zip(db_tokens, full_tokens):
            cursor.execute('UPDATE tokens SET text = ? WHERE id = ?', (new_text, token_id))
            updated += 1

        if (surah * 1000 + ayah) % 500 == 0:
            print(f"Processed {surah}:{ayah}...")

    print(f"\nCommitting changes...")
    conn.commit()
    conn.close()

    print(f"\nSuccess! Updated {updated} tokens")
    print(f"Skipped {skipped} verses (token count mismatch)")


if __name__ == "__main__":
    db_path = Path(__file__).parent.parent / "data" / "database" / "kalima.db"

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    print("=" * 60)
    print("WARNING: This will replace ALL token text with verse_texts!")
    print("=" * 60)
    response = input("Continue? (yes/no): ")

    if response.lower() != "yes":
        print("Cancelled.")
        sys.exit(0)

    fix_tokens(db_path)
