#!/usr/bin/env python3
"""
Smart restoration of token diacritics by matching verse text to DB tokens.
Handles compound words, Bismillah, and special cases.
"""

import sqlite3
import sys
from pathlib import Path


def normalize(text):
    """Remove diacritics for matching."""
    diacritics = 'َُِّْٰٓٔٱًٌٍۭۢ'
    return ''.join(c for c in text if c not in diacritics)


def find_best_match(verse_tokens, db_tokens):
    """
    Match verse tokens to DB tokens, handling compound words.
    Returns list of tuples: (db_token_index, matched_verse_text)
    """
    matches = []
    verse_idx = 0

    for db_idx, db_token in enumerate(db_tokens):
        if verse_idx >= len(verse_tokens):
            # No more verse tokens - use what we have
            matches.append((db_idx, db_token))
            continue

        # Normalize DB token
        db_norm = normalize(db_token)

        # Try single token match first
        verse_norm = normalize(verse_tokens[verse_idx])

        if db_norm == verse_norm:
            # Perfect match
            matches.append((db_idx, verse_tokens[verse_idx]))
            verse_idx += 1
        else:
            # Try compound match (DB token might be 2+ verse tokens combined)
            combined = verse_tokens[verse_idx]
            combined_norm = verse_norm
            lookahead = 1

            while verse_idx + lookahead < len(verse_tokens):
                next_token = verse_tokens[verse_idx + lookahead]
                combined_norm_test = normalize(combined + next_token)

                if combined_norm_test == db_norm:
                    # Found compound match
                    combined = combined + next_token
                    matches.append((db_idx, combined))
                    verse_idx += lookahead + 1
                    break

                combined += next_token
                lookahead += 1
            else:
                # No compound match found - use DB token as-is
                matches.append((db_idx, db_token))
                verse_idx += 1

    return matches


def restore_all_tokens(db_path):
    """Restore diacritics to all tokens using smart matching."""
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
    bismillah_pattern = normalize("بسم الله الرحمن الرحيم")

    for surah, ayah, verse_text in verses:
        # Get DB tokens
        db_token_rows = cursor.execute('''
            SELECT id, text
            FROM tokens
            WHERE verse_surah = ? AND verse_ayah = ?
            ORDER BY token_index
        ''', (surah, ayah)).fetchall()

        if not db_token_rows:
            continue

        db_token_ids = [row[0] for row in db_token_rows]
        db_tokens = [row[1] for row in db_token_rows]

        # Split verse text
        verse_tokens = verse_text.strip().split()

        # Remove Bismillah from verse tokens if it's there but not in DB
        verse_norm = normalize(' '.join(verse_tokens))
        if bismillah_pattern in verse_norm and len(db_tokens) < len(verse_tokens):
            # Check if first 4 tokens are Bismillah
            first_four = ' '.join(verse_tokens[:4])
            if normalize(first_four) == bismillah_pattern:
                verse_tokens = verse_tokens[4:]  # Skip Bismillah

        # Match tokens
        if len(db_tokens) == len(verse_tokens):
            # Simple 1:1 matching
            for token_id, verse_token in zip(db_token_ids, verse_tokens):
                cursor.execute('UPDATE tokens SET text = ? WHERE id = ?', (verse_token, token_id))
                updated += 1
        else:
            # Smart matching for compound words
            matches = find_best_match(verse_tokens, db_tokens)

            if len(matches) != len(db_tokens):
                print(f"SKIP {surah}:{ayah} - matching failed: {len(matches)} vs {len(db_tokens)}")
                skipped += 1
                continue

            for token_id, (_, matched_text) in zip(db_token_ids, matches):
                cursor.execute('UPDATE tokens SET text = ? WHERE id = ?', (matched_text, token_id))
                updated += 1

        if (surah * 1000 + ayah) % 500 == 0:
            print(f"Processed {surah}:{ayah}...")

    print(f"\nCommitting changes...")
    conn.commit()
    conn.close()

    print(f"\nSuccess! Updated {updated} tokens")
    if skipped > 0:
        print(f"Skipped {skipped} verses")


if __name__ == "__main__":
    db_path = Path(__file__).parent.parent / "data" / "database" / "kalima.db"

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    print("=" * 60)
    print("Smart token diacritic restoration")
    print("=" * 60)
    response = input("Continue? (yes/no): ")

    if response.lower() != "yes":
        print("Cancelled.")
        sys.exit(0)

    restore_all_tokens(db_path)
