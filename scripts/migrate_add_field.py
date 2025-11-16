#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import tempfile
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Add a field to verse/token/annotation objects in quran.jsonl."
    )
    parser.add_argument(
        "--scope",
        choices=["verse", "token", "annotation"],
        required=True,
        help="Where to add the field.",
    )
    parser.add_argument(
        "--field-name",
        required=True,
        help="Name of the field to add.",
    )
    parser.add_argument(
        "--default",
        required=True,
        help="Default value as a JSON literal (e.g. 'null', '\"YA\"', '0', '[]', '{}').",
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


def load_default(default_str: str) -> Any:
    try:
        return json.loads(default_str)
    except json.JSONDecodeError as e:
        raise SystemExit(f"Cannot parse --default as JSON: {e}")


def add_field_to_verse(obj: dict, field_name: str, default_value: Any) -> None:
    if field_name not in obj:
        obj[field_name] = default_value


def add_field_to_tokens(obj: dict, field_name: str, default_value: Any) -> None:
    tokens = obj.get("tokens", [])
    if not isinstance(tokens, list):
        return
    for t in tokens:
        if isinstance(t, dict) and field_name not in t:
            t[field_name] = default_value


def add_field_to_annotations(obj: dict, field_name: str, default_value: Any) -> None:
    anns = obj.get("annotations", [])
    if not isinstance(anns, list):
        return
    for a in anns:
        if isinstance(a, dict) and field_name not in a:
            a[field_name] = default_value


def main() -> None:
    args = parse_args()
    default_value = load_default(args.default)

    input_path = args.input
    output_path = args.output or input_path

    if not os.path.isfile(input_path):
        raise SystemExit(f"Input file not found: {input_path}")

    tmp_fd, tmp_path = tempfile.mkstemp(prefix="quran_migrate_", suffix=".jsonl")
    os.close(tmp_fd)

    modified_count = 0
    total_count = 0

    try:
        with open(input_path, "r", encoding="utf-8") as fin, \
             open(tmp_path, "w", encoding="utf-8") as fout:
            for line in fin:
                line = line.strip()
                if not line:
                    continue
                total_count += 1
                obj = json.loads(line)

                before = json.dumps(obj, sort_keys=True)
                if args.scope == "verse":
                    add_field_to_verse(obj, args.field_name, default_value)
                elif args.scope == "token":
                    add_field_to_tokens(obj, args.field_name, default_value)
                elif args.scope == "annotation":
                    add_field_to_annotations(obj, args.field_name, default_value)

                after = json.dumps(obj, sort_keys=True)
                if before != after:
                    modified_count += 1

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

        print(f"Total verse objects processed: {total_count}")
        print(f"Objects modified (at least one new field added): {modified_count}")

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


if __name__ == "__main__":
    main()
