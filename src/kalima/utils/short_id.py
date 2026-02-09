"""Sequential short ID generation with in-memory cache.

Format: prefix_number (e.g., "entry_123")
"""

import re
from typing import Optional

# In-memory cache for last-issued ID number per type
_id_cache: dict[str, int] = {}


def _get_next_number(conn, id_type: str) -> int:
    """Get the next available ID number for a given type.

    Uses SQL MAX on first call, then increments from cache.
    """
    if id_type in _id_cache:
        _id_cache[id_type] += 1
        return _id_cache[id_type]

    prefix = f"{id_type}_"
    prefix_len = len(prefix)
    max_number = 0

    table_name = {
        'entry': 'entries',
    }[id_type]

    try:
        row = conn.execute(
            f"SELECT MAX(CAST(SUBSTR(id, {prefix_len + 1}) AS INTEGER)) "
            f"FROM {table_name} WHERE id LIKE ?",
            (f"{prefix}%",)
        ).fetchone()
        val = row[0] if row else None
        if val:
            max_number = val
    except Exception:
        pass  # Table doesn't exist yet

    _id_cache[id_type] = max_number + 1
    return _id_cache[id_type]


def generate_entry_id(conn) -> str:
    return f"entry_{_get_next_number(conn, 'entry')}"


def is_short_id(id_str: str) -> bool:
    return bool(re.match(r'^entry_\d+$', id_str))


def get_short_id_prefix(id_str: str) -> Optional[str]:
    match = re.match(r'^(entry)_', id_str)
    return match.group(1) if match else None
