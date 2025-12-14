from __future__ import annotations

from pathlib import Path


def require_file(path: Path, *, label: str | None = None) -> Path:
    if not path.exists():
        prefix = f"{label}: " if label else ""
        raise FileNotFoundError(f"{prefix}{path} not found")
    if not path.is_file():
        prefix = f"{label}: " if label else ""
        raise FileNotFoundError(f"{prefix}{path} is not a file")
    return path

