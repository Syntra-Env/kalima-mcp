import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

MASAQ_PATH = Path("datasets/MASAQ.csv")
QC_PATH = Path("datasets/quranic-corpus-morphology-0.4.txt")
QURAN_CLEAN_PATH = Path("datasets/quran-clean.txt")
OUTPUT_PATH = Path("datasets/combined.jsonl")


def load_quran_clean() -> list:
    if not QURAN_CLEAN_PATH.exists():
        raise FileNotFoundError(f"Missing {QURAN_CLEAN_PATH}")
    with QURAN_CLEAN_PATH.open(encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

# Simple Buckwalter -> Arabic mapping for common characters.
BUCKWALTER_MAP = str.maketrans({
    "O": "ا", "I": "إ", "A": "أ", "G": "ء", "'": "ء", "|": "آ", "p": "ة", "t": "ت",
    "{": "أ", "}": "ى", "b": "ب", "P": "ب", "v": "ث", "j": "ج", "H": "ح", "x": "خ",
    "d": "د", "*": "ذ", "r": "ر", "z": "ز", "s": "س", "$": "ش", "S": "ص", "D": "ض",
    "T": "ط", "Z": "ظ", "E": "ع", "g": "غ", "_": "ـ", "f": "ف", "q": "ق", "k": "ك",
    "l": "ل", "m": "م", "n": "ن", "h": "ه", "w": "و", "Y": "ي", "y": "ي", " ": " ",
    "+": "َ", "^": "ً", "F": "ً", "K": "ٍ", "N": "ٌ", "o": "ُ", "u": "ُ", "i": "ِ",
    "a": "َ", "~": "ّ", "0": "٠", "1": "١", "2": "٢", "3": "٣", "4": "٤", "5": "٥",
    "6": "٦", "7": "٧", "8": "٨", "9": "٩",
})


def to_arabic(text: str) -> str:
    if not text:
        return text
    return text.translate(BUCKWALTER_MAP)


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
    verse_texts = load_quran_clean()
    if len(verse_texts) < 6236:
        print(f"Warning: quran-clean.txt has only {len(verse_texts)} lines; expected 6236.")
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

    verse_counter = 0
    with OUTPUT_PATH.open("w", encoding="utf-8") as out:
        for (s, a), toks in sorted(verses.items()):
            token_list = []
            clean_text = verse_texts[verse_counter] if verse_counter < len(verse_texts) else ""
            clean_words = clean_text.split()
            max_w = max(toks.keys()) if toks else 0

            for idx in range(1, max_w + 1):
                form, segments = toks.get(idx, ("", []))
                if idx - 1 < len(clean_words):
                    token_form = clean_words[idx - 1]
                else:
                    token_form = to_arabic(form) or form

                norm_segments = []
                for seg in segments:
                    seg_copy = dict(seg)
                    if seg_copy.get("form"):
                        seg_copy["form"] = to_arabic(seg_copy["form"])
                    if seg_copy.get("lemma"):
                        seg_copy["lemma"] = to_arabic(seg_copy["lemma"])
                    if seg_copy.get("root"):
                        seg_copy["root"] = to_arabic(seg_copy["root"])
                    norm_segments.append(seg_copy)

                # If no segments, still emit token to preserve verse shape.
                if not norm_segments:
                    norm_segments.append(
                        {
                            "type": "Stem",
                            "form": token_form,
                            "root": None,
                            "lemma": None,
                            "pattern": None,
                            "pos": None,
                            "verb_form": None,
                            "voice": None,
                            "mood": None,
                            "aspect": None,
                            "person": None,
                            "number": None,
                            "gender": None,
                            "case": None,
                            "dependency_rel": None,
                            "role": None,
                        }
                    )

                token_list.append(
                    {
                        "form": token_form,
                        "segments": norm_segments,
                    }
                )
            record = {
                "surah": {"number": s, "name": None},
                "ayah": a,
                "text": clean_text if clean_text else None,
                "tokens": token_list,
            }
            verse_counter += 1
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
