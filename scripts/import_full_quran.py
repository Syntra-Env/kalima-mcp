#!/usr/bin/env python3
"""
Import full Quran text from quran-clean.txt into corpus/quran.jsonl
Includes Arabic surah names and proper verse structure according to schema
"""

import json
import os
from datetime import datetime

# Complete mapping of Surah numbers to Arabic names (1-114)
SURAH_NAMES = {
    1: "الفاتحة", 2: "البقرة", 3: "آل عمران", 4: "النساء", 5: "المائدة",
    6: "الأنعام", 7: "الأعراف", 8: "الأنفال", 9: "التوبة", 10: "يونس",
    11: "هود", 12: "يوسف", 13: "الرعد", 14: "إبراهيم", 15: "الحجر",
    16: "النحل", 17: "الإسراء", 18: "الكهف", 19: "مريم", 20: "طه",
    21: "الأنبياء", 22: "الحج", 23: "المؤمنون", 24: "النور", 25: "الفرقان",
    26: "الشعراء", 27: "النمل", 28: "القصص", 29: "العنكبوت", 30: "الروم",
    31: "لقمان", 32: "السجدة", 33: "الأحزاب", 34: "سبأ", 35: "فاطر",
    36: "يس", 37: "الصافات", 38: "ص", 39: "الزمر", 40: "غافر",
    41: "فصلت", 42: "الشورى", 43: "الزخرف", 44: "الدخان", 45: "الجاثية",
    46: "الأحقاف", 47: "محمد", 48: "الفتح", 49: "الحجرات", 50: "ق",
    51: "الذاريات", 52: "الطور", 53: "النجم", 54: "القمر", 55: "الرحمن",
    56: "الواقعة", 57: "الحديد", 58: "المجادلة", 59: "الحشر", 60: "الممتحنة",
    61: "الصف", 62: "الجمعة", 63: "المنافقون", 64: "التغابن", 65: "الطلاق",
    66: "التحريم", 67: "الملك", 68: "القلم", 69: "الحاقة", 70: "المعارج",
    71: "نوح", 72: "الجن", 73: "المزمل", 74: "المدثر", 75: "القيامة",
    76: "الإنسان", 77: "المرسلات", 78: "النبأ", 79: "النازعات", 80: "عبس",
    81: "التكوير", 82: "الإنفطار", 83: "المطففين", 84: "الإنشقاق", 85: "البروج",
    86: "الطارق", 87: "الأعلى", 88: "الغاشية", 89: "الفجر", 90: "البلد",
    91: "الشمس", 92: "الليل", 93: "الضحى", 94: "الشرح", 95: "التين",
    96: "العلق", 97: "القدر", 98: "البينة", 99: "الزلزلة", 100: "العاديات",
    101: "القارعة", 102: "التكاثر", 103: "العصر", 104: "الهمزة", 105: "الفيل",
    106: "قريش", 107: "الماعون", 108: "الكوثر", 109: "الكافرون", 110: "النصر",
    111: "المسد", 112: "الإخلاص", 113: "الفلق", 114: "الناس"
}

# Ayah counts per surah (1-114)
AYAH_COUNTS = [
    7, 286, 200, 176, 120, 165, 206, 75, 129, 109,
    123, 111, 43, 52, 99, 128, 111, 110, 98, 135,
    112, 78, 118, 64, 77, 227, 93, 88, 69, 60,
    34, 30, 73, 54, 45, 83, 182, 88, 75, 85,
    54, 53, 89, 59, 37, 35, 38, 29, 18, 45,
    60, 49, 62, 55, 78, 96, 29, 22, 24, 13,
    14, 11, 11, 18, 12, 12, 30, 52, 52, 44,
    28, 28, 20, 56, 40, 31, 50, 40, 46, 42,
    29, 19, 36, 25, 22, 17, 19, 26, 30, 20,
    15, 21, 11, 8, 8, 19, 5, 8, 8, 11,
    11, 8, 3, 9, 5, 4, 7, 3, 6, 3,
    5, 4, 5, 6
]


def parse_quran_clean(filepath):
    """
    Parse quran-clean.txt and return list of verse objects

    Format: One ayah per line, ordered sequentially
    Lines 1-7: Surah 1 (7 ayahs)
    Lines 8-293: Surah 2 (286 ayahs)
    etc.
    """
    verses = []

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    line_idx = 0
    for surah_num in range(1, 115):  # 1 to 114
        ayah_count = AYAH_COUNTS[surah_num - 1]
        surah_name = SURAH_NAMES[surah_num]

        for ayah_num in range(1, ayah_count + 1):
            if line_idx >= len(lines):
                print(f"Warning: Ran out of lines at Surah {surah_num}, Ayah {ayah_num}")
                break

            verse = {
                "surah": {
                    "number": surah_num,
                    "name": surah_name
                },
                "ayah": ayah_num,
                "text": lines[line_idx],
                "tokens": [],
                "annotations": []
            }

            verses.append(verse)
            line_idx += 1

    return verses


def backup_corpus(corpus_path):
    """Create timestamped backup of existing corpus"""
    if os.path.exists(corpus_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{corpus_path}.backup_{timestamp}"

        with open(corpus_path, 'r', encoding='utf-8') as src:
            with open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())

        print(f"[OK] Backed up existing corpus to: {backup_path}")
        return backup_path
    return None


def write_corpus(verses, output_path):
    """Write verses to JSONL format"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for verse in verses:
            f.write(json.dumps(verse, ensure_ascii=False) + '\n')


def update_metadata(metadata_path, verse_count):
    """Update corpus metadata"""
    metadata = {
        "version": "1.0.0",
        "source": "Tanzil Project - quran-clean.txt (Uthmani 1.0.2)",
        "import_date": datetime.now().isoformat(),
        "verse_count": verse_count,
        "surah_count": 114,
        "schema_version": "0.1.0",
        "notes": "Full Quran import with Arabic surah names"
    }

    with open(metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"[OK] Updated metadata: {verse_count} verses, 114 surahs")


def main():
    # Paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_file = os.path.join(project_root, 'data', 'quran-clean.txt')
    corpus_file = os.path.join(project_root, 'corpus', 'quran.jsonl')
    metadata_file = os.path.join(project_root, 'corpus', 'metadata.json')

    print("=" * 60)
    print("Codex: Full Quran Import")
    print("=" * 60)

    # Check source file
    if not os.path.exists(data_file):
        print(f"[ERROR] Source file not found: {data_file}")
        return 1

    # Backup existing corpus
    backup_corpus(corpus_file)

    # Parse and import
    print(f"\nParsing {data_file}...")
    verses = parse_quran_clean(data_file)

    print(f"[OK] Parsed {len(verses)} verses")

    # Verify counts
    expected = sum(AYAH_COUNTS)
    if len(verses) != expected:
        print(f"[WARNING] Expected {expected} verses, got {len(verses)}")

    # Show sample
    print(f"\nSample verses:")
    for i in [0, 1, 2, -3, -2, -1]:  # First 3 and last 3
        v = verses[i]
        try:
            print(f"  {v['surah']['number']}:{v['ayah']} ({v['surah']['name']}) - {v['text'][:40]}...")
        except UnicodeEncodeError:
            print(f"  {v['surah']['number']}:{v['ayah']} (Surah #{v['surah']['number']}) - [Arabic text]")

    # Write corpus
    print(f"\nWriting corpus to {corpus_file}...")
    write_corpus(verses, corpus_file)
    print(f"[OK] Wrote {len(verses)} verses")

    # Update metadata
    update_metadata(metadata_file, len(verses))

    print(f"\n{'=' * 60}")
    print(f"[SUCCESS] Import complete!")
    print(f"{'=' * 60}")
    print(f"\nCorpus: {corpus_file}")
    print(f"Verses: {len(verses)}")
    print(f"Surahs: 114")
    print(f"\nNext steps:")
    print(f"  1. Run: python scripts/validate_corpus.py")
    print(f"  2. Begin annotation with interactive TUI (coming soon)")

    return 0


if __name__ == '__main__':
    exit(main())
