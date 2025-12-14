#!/usr/bin/env python3
"""
Restore full diacritics to tokens table by matching them with verse_texts.
Splits the fully-vocalized verse text and updates tokens accordingly.
"""

import sqlite3
import sys
import re
from pathlib import Path


def normalize_for_matching(text):
    """Remove all diacritics and whitespace for matching purposes."""
    # Common Arabic diacritics
    diacritics = 'َُِّْٰٓٔٱ'
    return ''.join(c for c in text if c not in diacritics and not c.isspace())


def split_verse_preserving_diacritics(verse_text):
    """Split verse text into tokens, preserving diacritics."""
    # Split on whitespace
    return verse_text.strip().split()


def restore_diacritics(db_path):
    """Restore diacritics to tokens by matching with verse_texts."""
    print(f"Opening database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all verses
    print("Fetching verses...")
    verses = cursor.execute('''
        SELECT surah_number, ayah_number, text
        FROM verse_texts
        ORDER BY surah_number, ayah_number
    ''').fetchall()

    print(f"Found {len(verses)} verses")

    updated_count = 0
    mismatch_count = 0

    for surah, ayah, full_text in verses:
        # Get tokens for this verse
        tokens = cursor.execute('''
            SELECT id, token_index, text
            FROM tokens
            WHERE verse_surah = ? AND verse_ayah = ?
            ORDER BY token_index
        ''', (surah, ayah)).fetchall()

        if not tokens:
            continue

        # Split verse text into fully-vocalized tokens
        full_tokens = split_verse_preserving_diacritics(full_text)

        if len(tokens) != len(full_tokens):
            print(f"WARNING {surah}:{ayah} - Token count mismatch: "
                  f"DB has {len(tokens)}, verse text splits to {len(full_tokens)}")
            mismatch_count += 1
            continue

        # Update each token with full diacritics
        for (token_id, token_idx, db_token), full_token in zip(tokens, full_tokens):
            # Verify they match (ignoring diacritics)
            normalized_db = normalize_for_matching(db_token)
            normalized_full = normalize_for_matching(full_token)

            if normalized_db != normalized_full:
                # Text mismatch - skip this token
                continue

            # Update with full diacritics
            if db_token != full_token:
                cursor.execute(
                    'UPDATE tokens SET text = ? WHERE id = ?',
                    (full_token, token_id)
                )
                updated_count += 1

        if (surah * 1000 + ayah) % 1000 == 0:
            print(f"Processed {surah}:{ayah}...")

    # Commit changes
    print(f"\nCommitting changes...")
    conn.commit()

    conn.close()

    print(f"\nSuccessfully updated {updated_count} tokens!")
    if mismatch_count > 0:
        print(f"Warning: {mismatch_count} verses had token count mismatches")


if __name__ == "__main__":
    db_path = Path(__file__).parent.parent / "data" / "database" / "kalima.db"

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    print("=" * 60)
    print("WARNING: This will modify the tokens table!")
    print("=" * 60)
    response = input("Continue? (yes/no): ")

    if response.lower() != "yes":
        print("Cancelled.")
        sys.exit(0)

    restore_diacritics(db_path)
