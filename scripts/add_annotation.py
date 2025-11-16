#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import tempfile
import time
from typing import Any, Dict, List, Optional, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add an annotation to a verse in corpus/quran.jsonl."
    )

    parser.add_argument(
        "--verse",
        required=True,
        help="Verse reference in the form SURAH:AYAH (e.g. '14:35').",
    )
    parser.add_argument(
        "--type",
        required=True,
        help="Annotation type (e.g. 'stylistic', 'rhetorical', 'comparative').",
    )
    parser.add_argument(
        "--note",
        required=True,
        help="The main annotation note text.",
    )

    parser.add_argument(
        "--subtype",
        default=None,
        help="Optional annotation subtype (e.g. 'prayer_introduction').",
    )
    parser.add_argument(
        "--scope",
        choices=["verse", "token", "span"],
        default="verse",
        help="Scope of the annotation (default: verse).",
    )
    parser.add_argument(
        "--tokens",
        default=None,
        help="Comma-separated list of target token IDs (e.g. '2,3,4'). Only meaningful for scope=token/span.",
    )
    parser.add_argument(
        "--tags",
        default=None,
        help="Comma-separated tags (e.g. 'ibrahim,dua,vocative').",
    )
    parser.add_argument(
        "--refs",
        default=None,
        help="Comma-separated verse refs for cross-reference (e.g. '2:126,14:35').",
    )
    parser.add_argument(
        "--status",
        default="raw",
        help="Status string for the annotation (default: 'raw').",
    )
    parser.add_argument(
        "--author",
        default="YA",
        help="Author identifier (default: 'YA').",
    )

    parser.add_argument(
        "--input",
        default=os.path.join("corpus", "quran.jsonl"),
        help="Path to input JSONL corpus (default: corpus/quran.jsonl).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to output JSONL corpus (default: in-place overwrite of input).",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="If doing in-place, save a .bak copy of the original.",
    )

    return parser.parse_args()


def parse_verse_ref(ref: str) -> Tuple[int, int]:
    try:
        s, a = ref.split(":")
        return int(s), int(a)
    except Exception:
        raise SystemExit(f"Invalid verse ref '{ref}'. Expected format 'SURAH:AYAH', e.g. '14:35'.")


def parse_int_list(arg: Optional[str]) -> List[int]:
    if arg is None or arg.strip() == "":
        return []
    parts = [p.strip() for p in arg.split(",") if p.strip()]
    try:
        return [int(p) for p in parts]
    except ValueError:
        raise SystemExit(f"Invalid integer list in '--tokens': {arg}")


def parse_str_list(arg: Optional[str]) -> List[str]:
    if arg is None or arg.strip() == "":
        return []
    return [p.strip() for p in arg.split(",") if p.strip()]


def generate_annotation_id(surah: int, ayah: int) -> str:
    """
    Generate a reasonably unique, readable annotation ID.
    Example: a-20251114-223045-014-035
    """
    ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    return f"a-{ts}-{surah:03d}-{ayah:03d}"


def build_annotation(
    surah: int,
    ayah: int,
    a_type: str,
    note: str,
    subtype: Optional[str],
    scope: str,
    token_ids: List[int],
    tags: List[str],
    refs: List[str],
    status: str,
    author: Optional[str],
) -> Dict[str, Any]:
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    ann: Dict[str, Any] = {
        "id": generate_annotation_id(surah, ayah),
        "type": a_type,
        "subtype": subtype,
        "scope": scope,
        "target_token_ids": token_ids,
        "note": note,
        "refs": refs,
        "tags": tags,
        "status": status,
        "created_at": now_iso,
        "updated_at": None,
        "author": author,
    }
    return ann


def main() -> None:
    args = parse_args()

    surah, ayah = parse_verse_ref(args.verse)
    token_ids = parse_int_list(args.tokens)
    tags = parse_str_list(args.tags)
    refs = parse_str_list(args.refs)

    input_path = args.input
    output_path = args.output or input_path

    if not os.path.isfile(input_path):
        raise SystemExit(f"Input file not found: {input_path}")

    tmp_fd, tmp_path = tempfile.mkstemp(prefix="quran_add_ann_", suffix=".jsonl")
    os.close(tmp_fd)

    found_verse = False
    total_verses = 0

    annotation_to_add = build_annotation(
        surah=surah,
        ayah=ayah,
        a_type=args.type,
        note=args.note,
        subtype=args.subtype,
        scope=args.scope,
        token_ids=token_ids,
        tags=tags,
        refs=refs,
        status=args.status,
        author=args.author,
    )

    try:
        with open(input_path, "r", encoding="utf-8") as fin, \
             open(tmp_path, "w", encoding="utf-8") as fout:
            for line in fin:
                line_stripped = line.strip()
                if not line_stripped:
                    continue

                total_verses += 1
                obj = json.loads(line_stripped)

                if int(obj.get("surah", -1)) == surah and int(obj.get("ayah", -1)) == ayah:
                    found_verse = True

                    anns = obj.get("annotations")
                    if not isinstance(anns, list):
                        anns = []
                    anns.append(annotation_to_add)
                    obj["annotations"] = anns

                fout.write(json.dumps(obj, ensure_ascii=False))
                fout.write("\n")

        if not found_verse:
            raise SystemExit(f"Verse {surah}:{ayah} not found in corpus {input_path}.")

        if output_path == input_path:
            if args.backup:
                backup_path = input_path + ".bak"
                shutil.copy2(input_path, backup_path)
                print(f"Backup written to {backup_path}")
            shutil.move(tmp_path, input_path)
            print(f"Annotation added to verse {surah}:{ayah} in-place ({input_path}).")
        else:
            shutil.move(tmp_path, output_path)
            print(f"Annotation added to verse {surah}:{ayah} in {output_path}.")

        print(f"Total verse objects processed: {total_verses}")
        print(f"Annotation ID: {annotation_to_add['id']}")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    main()
