from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def datasets_dir() -> Path:
    return repo_root() / "datasets"


def data_dir() -> Path:
    return repo_root() / "data"

