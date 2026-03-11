"""Download Sahih International translation and load into traditional_interpretations.

This data is ISOLATED in the traditional_interpretations table.
It is never used by HUFD, UOR, resonance, phase-lock, or any math pipeline.
It exists solely for comparison/audit purposes.
"""

import sys
import os
import re
import time
import json
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.db import get_connection, save_database

API_BASE = "https://api.quran.com/api/v4/quran/translations/20"
SOURCE = "sahih_international"
TOTAL_SURAHS = 114
CACHE_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'sahih_international.json')


def strip_footnotes(text: str) -> str:
    """Remove HTML footnote tags from translation text."""
    return re.sub(r'<sup.*?</sup>', '', text).strip()


def fetch_chapter(surah: int) -> list[str]:
    """Fetch a single chapter using curl (handles headers/encoding properly)."""
    url = f"{API_BASE}?chapter_number={surah}"
    result = subprocess.run(
        ["curl", "-s", "-H", "Accept: application/json",
         "-H", "User-Agent: Mozilla/5.0", url],
        capture_output=True, timeout=30
    )
    raw = result.stdout
    # Try UTF-8 first, fall back to latin-1
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError:
        text = raw.decode('latin-1')

    data = json.loads(text)
    translations = data.get('translations', [])
    return [strip_footnotes(t['text']) for t in translations]


def download_all() -> dict:
    """Download all 114 surahs from quran.com API. Returns {surah: [texts]}."""
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        print(f"Loaded cache with {len(cached)} surahs")
    else:
        cached = {}

    for surah in range(1, TOTAL_SURAHS + 1):
        if str(surah) in cached:
            continue

        print(f"Downloading surah {surah}/114...", end=" ", flush=True)

        try:
            texts = fetch_chapter(surah)
            cached[str(surah)] = texts
            print(f"{len(texts)} ayat")

            # Save cache incrementally
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(cached, f, ensure_ascii=False)

            # Rate limit: be polite to the API
            time.sleep(0.5)

        except Exception as e:
            print(f"Error: {e}")
            print(f"Cache saved. Re-run to resume from surah {surah}.")
            break

    print(f"\nDownload complete: {len(cached)} surahs cached.")
    return cached


def load_into_db(data: dict):
    """Bulk-insert translations into traditional_interpretations table."""
    conn = get_connection()

    existing = conn.execute(
        "SELECT COUNT(*) FROM traditional_interpretations WHERE source = ?",
        (SOURCE,)
    ).fetchone()[0]

    if existing > 0:
        print(f"Found {existing} existing Sahih International entries. Replacing...")
        conn.execute("DELETE FROM traditional_interpretations WHERE source = ?", (SOURCE,))

    count = 0
    for surah_str in sorted(data.keys(), key=int):
        surah = int(surah_str)
        texts = data[surah_str]
        for ayah_idx, text in enumerate(texts):
            ayah = ayah_idx + 1
            conn.execute(
                """INSERT OR REPLACE INTO traditional_interpretations
                   (surah, ayah, source, interpretation, language)
                   VALUES (?, ?, ?, ?, 'en')""",
                (surah, ayah, SOURCE, text)
            )
            count += 1

    save_database()
    print(f"Loaded {count} verses into traditional_interpretations (source='{SOURCE}').")


def main():
    print("=== Sahih International Loader ===")
    print("Target: traditional_interpretations table (ISOLATED from math pipeline)\n")

    data = download_all()
    if not data:
        print("No data downloaded.")
        return

    total_verses = sum(len(v) for v in data.values())
    print(f"\nTotal: {len(data)} surahs, {total_verses} verses")

    load_into_db(data)


if __name__ == "__main__":
    main()
