#!/usr/bin/env python3
import json
import os
from typing import Any, Dict, List


RAW_PATH = os.path.join("raw", "quran_raw.json")
OUT_PATH = os.path.join("corpus", "quran.jsonl")


def is_list_of_verses(obj: Any) -> bool:
    return isinstance(obj, list) and all(isinstance(x, dict) for x in obj)


def is_surah_ayah_map(obj: Any) -> bool:
    # {"1": {"1": "...", "2": "..."}, "2": {...}}
    return isinstance(obj, dict) and all(
        isinstance(v, dict) for v in obj.values()
    )


def normalize_from_list(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    verses = []
    for item in data:
        # try common key names
        surah = item.get("surah") or item.get("sura") or item.get("chapter")
        ayah = item.get("ayah") or item.get("verse") or item.get("aya")
        text = item.get("text") or item.get("arabic") or item.get("ar")

        if surah is None or ayah is None or text is None:
            # skip malformed entries
            continue

        verses.append({
            "surah": int(surah),
            "ayah": int(ayah),
            "text": text,
        })
    return verses


def normalize_from_map(data: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
    verses = []
    for s_key, surah_obj in data.items():
        try:
            surah_num = int(s_key)
        except ValueError:
            continue
        if not isinstance(surah_obj, dict):
            continue
        for a_key, text in surah_obj.items():
            try:
                ayah_num = int(a_key)
            except ValueError:
                continue
            verses.append({
                "surah": surah_num,
                "ayah": ayah_num,
                "text": text,
            })
    return verses


def main() -> None:
    if not os.path.isfile(RAW_PATH):
        raise SystemExit(f"Raw Quran JSON not found at {RAW_PATH}")

    with open(RAW_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if is_list_of_verses(data):
        verses = normalize_from_list(data)
    elif is_surah_ayah_map(data):
        verses = normalize_from_map(data)
    else:
        raise SystemExit(
            "Unsupported quran_raw.json structure. "
            "Expected either a list of objects or a {surah:{ayah:text}} map."
        )

    # sort by surah, then ayah
    verses.sort(key=lambda v: (v["surah"], v["ayah"]))

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)

    with open(OUT_PATH, "w", encoding="utf-8") as out:
        for v in verses:
            obj = {
                "surah": v["surah"],
                "ayah": v["ayah"],
                "text": v["text"],
                "text_norm": None,
                "section_tags": [],
                "tokens": [],
                "annotations": [],
            }
            out.write(json.dumps(obj, ensure_ascii=False))
            out.write("\n")

    print(f"Wrote {len(verses)} verses to {OUT_PATH}")


if __name__ == "__main__":
    main()
