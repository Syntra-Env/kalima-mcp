from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Iterator


def read_lines(path: Path, *, encoding: str = "utf-8") -> list[str]:
    with path.open("r", encoding=encoding) as f:
        return [line.rstrip("\n") for line in f]


def iter_jsonl(path: Path, *, encoding: str = "utf-8") -> Iterator[dict[str, Any]]:
    with path.open("r", encoding=encoding) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]], *, encoding: str = "utf-8") -> None:
    with path.open("w", encoding=encoding) as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, obj: Any, *, encoding: str = "utf-8", indent: int = 2) -> None:
    with path.open("w", encoding=encoding) as f:
        json.dump(obj, f, ensure_ascii=False, indent=indent)

