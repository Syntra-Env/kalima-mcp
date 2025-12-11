#!/usr/bin/env python3
"""
Build complete combined.jsonl from source datasets.

Merges:
- Quranic.csv: morphological and syntactic annotations
- quran-clean.txt: verse text
- (Optional) surah metadata for names

Output: combined.jsonl with all fields populated
"""

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

def load_verse_text(quran_file):
    """Load verse text indexed by sequential verse number."""
    verses = []
    with open(quran_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                verses.append(line)
    return verses

def null_if_underscore(value):
    """Convert underscore to None, otherwise return value."""
    return None if value == '_' else (value if value else None)

def parse_quranic_csv(quranic_csv):
    """
    Parse Quranic.csv and group by verse, then by word (token), then segments.

    Returns: dict[surah:ayah] -> list of tokens, each with list of segments
    """
    verses = defaultdict(lambda: defaultdict(list))

    with open(quranic_csv, 'r', encoding='utf-16') as f:
        reader = csv.DictReader(f, delimiter='\t')

        for row in reader:
            loc = row['location']
            if loc == '_':  # Skip root node
                continue

            # Parse location: (chapter:verse:word:segment)
            parts = loc.strip('()').split(':')
            if len(parts) != 4:
                continue

            chapter, verse, word, segment = parts
            verse_ref = f"{chapter}:{verse}"
            word_idx = int(word) - 1  # 0-indexed

            # Build segment
            seg = {
                'type': null_if_underscore(row['segment']),
                'form': null_if_underscore(row['uthmani_token']),
                'root': null_if_underscore(row['root']),
                'lemma': null_if_underscore(row['lemma']),
                'pattern': None,  # Will add pattern extraction later
                'pos': null_if_underscore(row['pos']),
                'verb_form': null_if_underscore(row['verb_form']),
                'voice': null_if_underscore(row['verb_voice']),
                'mood': null_if_underscore(row['verb_mood']),
                'aspect': null_if_underscore(row['verb_aspect']),
                'person': null_if_underscore(row['person']),
                'number': null_if_underscore(row['number']),
                'gender': null_if_underscore(row['gender']),
                'case': null_if_underscore(row['nominal_case']),
                'dependency_rel': null_if_underscore(row['rel_label']),
                'role': null_if_underscore(row['pos_ar']),
                'derived_noun_type': null_if_underscore(row['derived_nouns']),
                'state': null_if_underscore(row['nominal_state']),
            }

            verses[verse_ref][word_idx].append(seg)

    return verses

def build_combined_jsonl(quranic_csv, quran_text, output_file):
    """Build the complete combined.jsonl file."""

    print("Loading verse text...")
    verse_texts = load_verse_text(quran_text)

    print("Parsing Quranic.csv...")
    verses_data = parse_quranic_csv(quranic_csv)

    print(f"Building combined.jsonl for {len(verses_data)} verses...")

    # Bismillah pattern to detect and strip (extract from first line which is 1:1)
    BISMILLAH = verse_texts[0] if verse_texts else 'بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ'

    # Surah metadata (names to be added manually later)
    # For now, just use numbers

    verse_counter = 0
    normalized_count = 0
    with open(output_file, 'w', encoding='utf-8') as out:
        # Iterate through surahs and ayahs in order
        for surah in range(1, 115):  # 114 surahs
            # Get ayah count for this surah (we'll detect from data)
            ayah_count = max(
                int(ref.split(':')[1])
                for ref in verses_data.keys()
                if int(ref.split(':')[0]) == surah
            ) if any(int(ref.split(':')[0]) == surah for ref in verses_data.keys()) else 0

            for ayah in range(1, ayah_count + 1):
                verse_ref = f"{surah}:{ayah}"

                if verse_ref not in verses_data:
                    print(f"Warning: No data for {verse_ref}", file=sys.stderr)
                    continue

                # Get verse text
                text = verse_texts[verse_counter] if verse_counter < len(verse_texts) else None
                verse_counter += 1

                # Build tokens from words
                tokens = []
                word_data = verses_data[verse_ref]
                for word_idx in sorted(word_data.keys()):
                    segments = word_data[word_idx]

                    # Token form is combination of all segment forms
                    token_form = ''.join(s['form'] or '' for s in segments)

                    token = {
                        'form': token_form,
                        'segments': segments
                    }
                    tokens.append(token)

                # Normalize verse text: strip Bismillah if present in text but not in tokens
                if text and text.startswith(BISMILLAH):
                    # Check if first token matches Bismillah start
                    first_token_form = tokens[0]['form'] if tokens else ''
                    if not first_token_form.startswith('بِسْمِ'):
                        # Bismillah is in text but not in tokens, strip it
                        text = text[len(BISMILLAH):].strip()
                        normalized_count += 1

                # Build verse entry
                verse_entry = {
                    'surah': {
                        'number': surah,
                        'name': None  # To be filled manually
                    },
                    'ayah': ayah,
                    'text': text,
                    'tokens': tokens
                }

                # Write JSONL
                out.write(json.dumps(verse_entry, ensure_ascii=False) + '\n')

    print(f"[OK] Written {verse_counter} verses to {output_file}")
    print(f"[OK] Normalized {normalized_count} verses (stripped Bismillah from text)")

def main():
    # Paths
    base_dir = Path(__file__).parent.parent
    quranic_csv = base_dir / 'datasets' / 'Quranic' / 'Quranic.csv'
    quran_text = base_dir / 'datasets' / 'quran-clean.txt'
    output = base_dir / 'datasets' / 'combined.jsonl'

    if not quranic_csv.exists():
        print(f"Error: {quranic_csv} not found", file=sys.stderr)
        sys.exit(1)

    if not quran_text.exists():
        print(f"Error: {quran_text} not found", file=sys.stderr)
        sys.exit(1)

    print(f"Input: {quranic_csv}")
    print(f"Input: {quran_text}")
    print(f"Output: {output}")
    print()

    build_combined_jsonl(str(quranic_csv), str(quran_text), str(output))

    print("\n[OK] Done! combined.jsonl written to datasets/.")

if __name__ == '__main__':
    main()
