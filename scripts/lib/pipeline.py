from __future__ import annotations

from contextlib import contextmanager
from time import perf_counter


@contextmanager
def step(name: str):
    start = perf_counter()
    print(f"[STEP] {name}...")
    try:
        yield
    finally:
        elapsed = perf_counter() - start
        print(f"[OK] {name} ({elapsed:.2f}s)")


def start_step(name: str):
    start = perf_counter()
    print(f"[STEP] {name}...")

    def end():
        elapsed = perf_counter() - start
        print(f"[OK] {name} ({elapsed:.2f}s)")

    return end
