import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

MASAQ_PATH = Path("datasets/MASAQ.csv")
QC_PATH = Path("datasets/quranic-corpus-morphology-0.4.txt")
OUTPUT_PATH = Path("combined.jsonl")


def clean(s: str) -> str:
    return s.strip() if s is not None else ""


def build_features(**kwargs) -> str:
    parts = []
    for k, v in kwargs.items():
        if v:
            parts.append(f"{k}:{v}")
    return " | ".join(parts) if parts else ""


def parse_masaq() -> Dict[Tuple[int, int, int], Tuple[str, List[dict]]]:
    data: Dict[Tuple[int, int, int], Tuple[str, List[dict]]] = {}
    with MASAQ_PATH.open(encoding="utf-8-sig", newline="") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            try:
                s = int(row["Sura_No"])
                a = int(row["Verse_No"])
                w = int(row["Word_No"])
            except (ValueError, KeyError):
                continue

            word = clean(row.get("Segmented_Word", "")) or clean(row.get("Word", ""))
            lemma = clean(row.get("Without_Diacritics", "")) or None
            pos = clean(row.get("Morph_tag", "")) or None
            seg_type = clean(row.get("Morph_type", "")) or "Stem"
            case = clean(row.get("Case_Mood", "")) or None
            role = clean(row.get("Syntactic_Role", "")) or None

            features = build_features(
                punct=clean(row.get("Punctuation_Mark", "")),
                invar=clean(row.get("Invariable_Declinable", "")),
                poss=clean(row.get("Possessive_Construct", "")),
                case_marker=clean(row.get("Case_Mood_Marker", "")),
                phrase=clean(row.get("Phrase", "")),
                phrase_fn=clean(row.get("Phrasal_Function", "")),
                notes=clean(row.get("Notes", "")),
            )

            segment = {
                "type": seg_type,
                "form": word,
                "root": None,
                "lemma": lemma,
                "pattern": features or None,
                "pos": pos,
                "verb_form": None,
                "voice": None,
                "mood": None,
                "tense": None,
                "aspect": None,
                "person": None,
                "number": None,
                "gender": None,
                "case": case,
                "dependency_rel": None,
                "role": role,
            }

            key = (s, a, w)
            data[key] = (word, [segment])
    return data


def parse_qc() -> Dict[Tuple[int, int, int], Tuple[str, List[dict]]]:
    data: Dict[Tuple[int, int, int], Tuple[str, List[dict]]] = {}
    tag_re = re.compile(r"^([A-Z_]+):(.*)$")

    def tag_lookup(tags: List[str], key: str) -> str:
        for t in tags:
            m = tag_re.match(t)
            if m and m.group(1) == key:
                return m.group(2)
        return ""

    def has_flag(tags: List[str], flag: str) -> bool:
        return any(t.upper() == flag.upper() for t in tags)

    with QC_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            ref = parts[0].strip("()").split(":")
            if len(ref) < 3:
                continue
            try:
                s = int(ref[0])
                a = int(ref[1])
                w = int(ref[2])
            except ValueError:
                continue
            surface = parts[1].strip()
            pos_col = parts[2].strip() or None
            tags = parts[3].split("|") if len(parts) > 3 else []

            seg_type = "Stem"
            for t in tags:
                if t.upper().startswith("PREFIX"):
                    seg_type = "Prefix"
                    break
                if t.upper().startswith("STEM"):
                    seg_type = "Stem"
            if not seg_type and tags:
                seg_type = tags[0]

            pos = tag_lookup(tags, "POS") or pos_col
            root = tag_lookup(tags, "ROOT") or None
            lemma = tag_lookup(tags, "LEM") or None
            case = tag_lookup(tags, "CASE")
            if not case:
                if has_flag(tags, "GEN"):
                    case = "GEN"
                elif has_flag(tags, "ACC"):
                    case = "ACC"
                elif has_flag(tags, "NOM"):
                    case = "NOM"

            dep = tag_lookup(tags, "DEP") or None
            role = tag_lookup(tags, "ROLE") or None

            segment = {
                "type": seg_type or "Stem",
                "form": surface,
                "root": root or None,
                "lemma": lemma or None,
                "pattern": None,
                "pos": pos or None,
                "verb_form": None,
                "voice": None,
                "mood": None,
                "tense": None,
                "aspect": None,
                "person": None,
                "number": None,
                "gender": None,
                "case": case or None,
                "dependency_rel": dep,
                "role": role,
            }

            key = (s, a, w)
            if key in data:
                data[key][1].append(segment)
            else:
                data[key] = (surface, [segment])
    return data


def merge_and_write(masaq, qc):
    verses: Dict[Tuple[int, int], Dict[int, Tuple[str, List[dict]]]] = defaultdict(dict)
    all_keys = set((s, a) for (s, a, _) in masaq.keys()) | set((s, a) for (s, a, _) in qc.keys())

    for (s, a) in all_keys:
        word_indices = set(
            w for (ss, aa, w) in masaq.keys() if ss == s and aa == a
        ) | set(w for (ss, aa, w) in qc.keys() if ss == s and aa == a)
        for w in sorted(word_indices):
            if (s, a, w) in masaq:
                verses[(s, a)][w] = masaq[(s, a, w)]
            elif (s, a, w) in qc:
                verses[(s, a)][w] = qc[(s, a, w)]

    with OUTPUT_PATH.open("w", encoding="utf-8") as out:
        for (s, a), toks in sorted(verses.items()):
            token_list = []
            for w, (form, segments) in sorted(toks.items()):
                token_list.append(
                    {
                        "form": form,
                        "segments": segments,
                    }
                )
            record = {
                "surah": {"number": s, "name": None},
                "ayah": a,
                "text": None,
                "tokens": token_list,
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")


def main():
    if not MASAQ_PATH.exists() or not QC_PATH.exists():
        raise SystemExit("Dataset files not found; expected datasets/MASAQ.csv and datasets/quranic-corpus-morphology-0.4.txt")
    masaq = parse_masaq()
    qc = parse_qc()
    merge_and_write(masaq, qc)
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
