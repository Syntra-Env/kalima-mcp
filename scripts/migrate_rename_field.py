#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import tempfile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rename a field in verse/token/annotation objects in quran.jsonl."
    )
    parser.add_argument(
        "--scope",
        choices=["verse", "token", "annotation"],
        required=True,
        help="Where to rename the field.",
    )
    parser.add_argument(
        "--old-name",
        required=True,
        help="Existing field name.",
    )
    parser.add_argument(
        "--new-name",
        required=True,
        help="New field name.",
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


def rename_in_verse(obj: dict, old: str, new: str) -> bool:
    if old in obj and new not in obj:
        obj[new] = obj.pop(old)
        return True
    return False


def rename_in_list(list_obj, old: str, new: str) -> int:
    count = 0
    if not isinstance(list_obj, list):
        return 0
    for item in list_obj:
        if isinstance(item, dict) and old in item and new not in item:
            item[new] = item.pop(old)
            count += 1
    return count


def main() -> None:
    args = parse_args()

    input_path = args.input
    output_path = args.output or input_path

    if not os.path.isfile(input_path):
        raise SystemExit(f"Input file not found: {input_path}")

    tmp_fd, tmp_path = tempfile.mkstemp(prefix="quran_migrate_", suffix=".jsonl")
    os.close(tmp_fd)

    total_verses = 0
    total_renamed_objects = 0

    try:
        with open(input_path, "r", encoding="utf-8") as fin, \
             open(tmp_path, "w", encoding="utf-8") as fout:
            for line in fin:
                line = line.strip()
                if not line:
                    continue
                total_verses += 1
                obj = json.loads(line)

                renamed_here = 0
                if args.scope == "verse":
                    if rename_in_verse(obj, args.old_name, args.new_name):
                        renamed_here += 1
                elif args.scope == "token":
                    renamed_here += rename_in_list(obj.get("tokens", []), args.old_name, args.new_name)
                elif args.scope == "annotation":
                    renamed_here += rename_in_list(obj.get("annotations", []), args.old_name, args.new_name)

                total_renamed_objects += renamed_here

                fout.write(json.dumps(obj, ensure_ascii=False))
                fout.write("\n")

        if output_path == input_path:
            if args.backup:
                backup_path = input_path + ".bak"
                shutil.copy2(input_path, backup_path)
                print(f"Backup written to {backup_path}")
            shutil.move(tmp_path, input_path)
            print(f"In-place update completed on {input_path}")
        else:
            shutil.move(tmp_path, output_path)
            print(f"Written updated corpus to {output_path}")

        print(f"Total verse objects processed: {total_verses}")
        print(f"Total objects where the field was renamed: {total_renamed_objects}")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    main()
