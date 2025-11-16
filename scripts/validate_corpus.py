#!/usr/bin/env python3
import argparse
import json
import os
from typing import List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lightweight structural validation for corpus/quran.jsonl."
    )
    parser.add_argument(
        "--input",
        default=os.path.join("corpus", "quran.jsonl"),
        help="Path to input JSONL corpus (default: corpus/quran.jsonl).",
    )
    return parser.parse_args()


def validate_verse(obj: dict) -> List[str]:
    errors = []

    # Required top-level fields
    for key in ["surah", "ayah", "text", "tokens", "annotations"]:
        if key not in obj:
            errors.append(f"Missing key: {key}")
    if errors:
        return errors

    # Basic type checks
    if not isinstance(obj["surah"], dict):
        errors.append("surah must be object (dict)")
    elif "number" not in obj["surah"] or "name" not in obj["surah"]:
        errors.append("surah must have 'number' and 'name' fields")
    elif not isinstance(obj["surah"].get("number"), int):
        errors.append("surah.number must be int")
    elif not isinstance(obj["surah"].get("name"), str):
        errors.append("surah.name must be string")
    if not isinstance(obj["ayah"], int):
        errors.append("ayah must be int")
    if not isinstance(obj["text"], str):
        errors.append("text must be string")
    if not isinstance(obj["tokens"], list):
        errors.append("tokens must be a list")
    if not isinstance(obj["annotations"], list):
        errors.append("annotations must be a list")

    # Token checks (very basic)
    if isinstance(obj.get("tokens"), list):
        for t in obj["tokens"]:
            if not isinstance(t, dict):
                errors.append("token is not an object")
                continue
            if "id" not in t or "form" not in t:
                errors.append("token missing 'id' or 'form'")
                continue
            if not isinstance(t["id"], int):
                errors.append("token.id must be int")
            if not isinstance(t["form"], str):
                errors.append("token.form must be string")

    # Annotation checks (basic)
    if isinstance(obj.get("annotations"), list):
        for a in obj["annotations"]:
            if not isinstance(a, dict):
                errors.append("annotation is not an object")
                continue
            for req in ["id", "type", "scope", "note"]:
                if req not in a:
                    errors.append(f"annotation missing '{req}'")
            if "scope" in a and a["scope"] not in ("verse", "token", "span"):
                errors.append(f"annotation.scope has unexpected value: {a.get('scope')}")

    return errors


def main() -> None:
    args = parse_args()
    input_path = args.input

    if not os.path.isfile(input_path):
        raise SystemExit(f"Input file not found: {input_path}")

    total = 0
    error_count = 0
    detailed_errors: List[Tuple[int, List[str]]] = []

    with open(input_path, "r", encoding="utf-8") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            total += 1
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                error_count += 1
                detailed_errors.append((line_number, [f"JSON decode error: {e}"]))
                continue

            errs = validate_verse(obj)
            if errs:
                error_count += 1
                detailed_errors.append((line_number, errs))

    print(f"Verses checked: {total}")
    print(f"Verses with errors: {error_count}")

    if error_count > 0:
        print("\nSample errors:")
        for line_no, errs in detailed_errors[:20]:
            print(f"- Line {line_no}:")
            for e in errs:
                print(f"    • {e}")


if __name__ == "__main__":
    main()
