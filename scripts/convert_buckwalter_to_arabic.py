#!/usr/bin/env python3
"""
Convert Buckwalter transliteration to Arabic script in the database.
Updates lemma and root fields in the segments table.
"""

import sqlite3
import sys
from pathlib import Path

# Buckwalter to Arabic mapping
BUCKWALTER_TO_ARABIC = {
    "'": "ء",
    "|": "آ",
    ">": "أ",
    "&": "ؤ",
    "<": "إ",
    "}": "ئ",
    "A": "ا",
    "b": "ب",
    "p": "ة",
    "t": "ت",
    "v": "ث",
    "j": "ج",
    "H": "ح",
    "x": "خ",
    "d": "د",
    "*": "ذ",
    "r": "ر",
    "z": "ز",
    "s": "س",
    "$": "ش",
    "S": "ص",
    "D": "ض",
    "T": "ط",
    "Z": "ظ",
    "E": "ع",
    "g": "غ",
    "_": "ـ",
    "f": "ف",
    "q": "ق",
    "k": "ك",
    "l": "ل",
    "m": "م",
    "n": "ن",
    "h": "ه",
    "w": "و",
    "Y": "ى",
    "y": "ي",
    "F": "ً",
    "N": "ٌ",
    "K": "ٍ",
    "a": "َ",
    "u": "ُ",
    "i": "ِ",
    "~": "ّ",
    "o": "ْ",
    "`": "ٰ",
    "{": "ٱ",
}


def buckwalter_to_arabic(text):
    """Convert Buckwalter transliteration to Arabic script."""
    if not text:
        return text

    result = []
    for char in text:
        result.append(BUCKWALTER_TO_ARABIC.get(char, char))
    return ''.join(result)


def convert_database(db_path):
    """Convert all Buckwalter fields in the database to Arabic."""
    print(f"Opening database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all segments with lemma or root in Buckwalter
    print("Fetching segments...")
    cursor.execute("SELECT id, lemma, root FROM segments WHERE lemma IS NOT NULL OR root IS NOT NULL")
    segments = cursor.fetchall()
    print(f"Found {len(segments)} segments to convert")

    # Convert each segment
    converted = 0
    for seg_id, lemma, root in segments:
        new_lemma = buckwalter_to_arabic(lemma) if lemma else None
        new_root = buckwalter_to_arabic(root) if root else None

        # Only update if something changed
        if new_lemma != lemma or new_root != root:
            cursor.execute(
                "UPDATE segments SET lemma = ?, root = ? WHERE id = ?",
                (new_lemma, new_root, seg_id)
            )
            converted += 1

            if converted % 1000 == 0:
                print(f"Converted {converted} segments...")

    # Commit changes
    print(f"Committing changes...")
    conn.commit()

    # Verify conversion
    print("\nVerifying conversion...")
    cursor.execute("SELECT form, lemma, root FROM segments WHERE lemma IS NOT NULL LIMIT 5")
    samples = cursor.fetchall()
    print("\nSample results:")
    for form, lemma, root in samples:
        print(f"  Form: {form}, Lemma: {lemma}, Root: {root}")

    conn.close()
    print(f"\n✓ Successfully converted {converted} segments!")


if __name__ == "__main__":
    db_path = Path(__file__).parent.parent / "data" / "database" / "kalima.db"

    if not db_path.exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)

    # Backup warning
    print("=" * 60)
    print("WARNING: This will modify the database!")
    print("=" * 60)
    response = input("Continue? (yes/no): ")

    if response.lower() != "yes":
        print("Cancelled.")
        sys.exit(0)

    convert_database(db_path)
