#!/usr/bin/env python3
"""
Import Quranic Corpus morphological data into corpus tokens
Parses quranic-corpus-morphology-0.4.txt and populates token arrays
"""

import json
import os
import sys
import re
from collections import defaultdict

# Handle Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')


def parse_morphology_file(filepath):
    """
    Parse Quranic Corpus morphology file
    Format: (surah:ayah:word:segment) form pos features
    """
    verses_data = defaultdict(lambda: defaultdict(list))

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('LOCATION'):
                continue

            parts = line.split('\t')
            if len(parts) < 4:
                continue

            location, form, tag, features = parts[0], parts[1], parts[2], parts[3]

            # Parse location (surah:ayah:word:segment)
            match = re.match(r'\((\d+):(\d+):(\d+):(\d+)\)', location)
            if not match:
                continue

            surah, ayah, word, segment = map(int, match.groups())

            # Parse features
            parsed_features = parse_features(features)

            # Store segment data
            segment_data = {
                'segment_id': segment,
                'form': form,
                'pos': tag,
                **parsed_features
            }

            verses_data[(surah, ayah)][word].append(segment_data)

    return verses_data


def parse_features(features_str):
    """Parse feature string into dict"""
    result = {}

    # Extract root: ROOT:xyz
    root_match = re.search(r'ROOT:(\w+)', features_str)
    if root_match:
        result['root'] = root_match.group(1)

    # Extract lemma: LEM:xyz
    lemma_match = re.search(r'LEM:([^\|]+)', features_str)
    if lemma_match:
        result['lemma'] = lemma_match.group(1)

    # Extract POS if in features
    pos_match = re.search(r'POS:(\w+)', features_str)
    if pos_match:
        result['pos_detail'] = pos_match.group(1)

    # Determine segment type
    if 'PREFIX' in features_str:
        result['type'] = 'prefix'
    elif 'SUFFIX' in features_str:
        result['type'] = 'suffix'
    elif 'STEM' in features_str:
        result['type'] = 'stem'
    else:
        result['type'] = 'unknown'

    # Store full features for reference
    result['features_raw'] = features_str

    return result


def load_corpus(corpus_path):
    """Load corpus verses"""
    verses = []
    with open(corpus_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                verses.append(json.loads(line))
    return verses


def populate_tokens(verses, morphology_data):
    """Populate token arrays in verses with morphology data"""
    populated = 0

    for verse in verses:
        surah = verse['surah']['number']
        ayah = verse['ayah']

        key = (surah, ayah)
        if key not in morphology_data:
            continue

        # Extract Arabic words from verse text
        arabic_text = verse.get('text', '')
        arabic_words = arabic_text.split()

        word_data = morphology_data[key]
        tokens = []

        # Sort words by ID
        for word_id in sorted(word_data.keys()):
            segments = word_data[word_id]

            # Use Arabic form from the verse text instead of transliteration
            # word_id is 1-indexed, array is 0-indexed
            if word_id <= len(arabic_words):
                word_form = arabic_words[word_id - 1]
            else:
                # Fallback: combine transliterated segments (shouldn't happen)
                word_form = ''.join(seg['form'] for seg in segments)

            token = {
                'id': word_id,
                'form': word_form,
                'segments': []
            }

            # Add segments with Arabic substrings
            # Note: We keep morphological metadata but don't display transliterated forms
            for segment in segments:
                # For segments, we keep them but without transliterated form display
                # The morphological data (root, lemma, features) is preserved
                token['segments'].append({
                    'id': f"{word_id}.{segment['segment_id']}",
                    'form': None,  # Set to None - we won't display segment forms, only morphological data
                    'type': segment['type'],
                    'pos': segment.get('pos_detail', segment['pos']),
                    'root': segment.get('root'),
                    'lemma': segment.get('lemma'),
                    'features': segment.get('features_raw')
                })

            tokens.append(token)

        verse['tokens'] = tokens
        populated += 1

    return populated


def save_corpus(verses, output_path):
    """Save corpus with populated tokens"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for verse in verses:
            f.write(json.dumps(verse, ensure_ascii=False) + '\n')


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    morphology_file = os.path.join(project_root, 'data', 'quranic-corpus-morphology-0.4.txt')
    corpus_file = os.path.join(project_root, 'corpus', 'quran.jsonl')

    print("=" * 60)
    print("Importing Quranic Corpus Morphological Data")
    print("=" * 60)

    # Check files exist
    if not os.path.exists(morphology_file):
        print(f"[ERROR] Morphology file not found: {morphology_file}")
        return 1

    if not os.path.exists(corpus_file):
        print(f"[ERROR] Corpus file not found: {corpus_file}")
        return 1

    # Parse morphology
    print(f"\nParsing morphology file...")
    morphology_data = parse_morphology_file(morphology_file)
    print(f"[OK] Parsed {len(morphology_data)} verses with morphological data")

    # Load corpus
    print(f"\nLoading corpus...")
    verses = load_corpus(corpus_file)
    print(f"[OK] Loaded {len(verses)} verses")

    # Populate tokens
    print(f"\nPopulating tokens with morphology...")
    populated = populate_tokens(verses, morphology_data)
    print(f"[OK] Populated {populated} verses with tokens")

    # Show sample
    print(f"\nSample (Surah 1, Ayah 1):")
    sample = next(v for v in verses if v['surah']['number'] == 1 and v['ayah'] == 1)
    print(f"Text: {sample['text']}")
    print(f"Tokens: {len(sample['tokens'])} words")
    for token in sample['tokens'][:3]:
        print(f"  [{token['id']}] {token['form']}")
        for seg in token['segments']:
            root_info = f" (root: {seg['root']})" if seg.get('root') else ""
            print(f"    - {seg['id']}: {seg['form']} [{seg['type']}]{root_info}")

    # Backup and save
    print(f"\nBacking up corpus...")
    backup_path = corpus_file + '.before_morphology'
    import shutil
    shutil.copy2(corpus_file, backup_path)
    print(f"[OK] Backup: {backup_path}")

    print(f"\nSaving corpus with populated tokens...")
    save_corpus(verses, corpus_file)
    print(f"[OK] Saved to {corpus_file}")

    print(f"\n{'=' * 60}")
    print(f"[SUCCESS] Morphology import complete!")
    print(f"{'=' * 60}")
    print(f"Verses with tokens: {populated}/{len(verses)}")
    print(f"\nNext: Run Quran reader to view and annotate")

    return 0


if __name__ == '__main__':
    exit(main())
