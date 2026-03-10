"""UOR content addressing for the Quranic compositional chain.

Computes content-derived addresses (SHA-256) bottom-up:
  atoms → morpheme_types → word_types → word_instances → verses

Each level's address is fully determined by the content below it.
Addresses are stored in a single `content_addresses` table.

Content addressing is lossless (exact identity). UOR dihedral canonical form
is a separate concern (lossy compression for equivalence classes) — it operates
on ring elements, not raw UTF-8 bytes, and would conflate unrelated characters.
"""

import hashlib
import sqlite3


def _sha256(data: bytes) -> str:
    """Return hex-encoded SHA-256 digest."""
    return hashlib.sha256(data).hexdigest()


def _atom_canonical(base_letter: str, diacritics: str) -> bytes:
    """Canonical byte form for an atom: UTF-8(base_letter) || UTF-8(diacritics)."""
    return (base_letter or '').encode('utf-8') + (diacritics or '').encode('utf-8')


def _sequence_canonical(child_addresses: list[str]) -> bytes:
    """Canonical byte form for a composition: ordered concatenation of child hex digests."""
    return b'|'.join(a.encode('ascii') for a in child_addresses)


# --- Table setup ---

def initialize_address_table(conn: sqlite3.Connection):
    """Create the content_addresses table (idempotent)."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS content_addresses (
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            address TEXT NOT NULL,
            PRIMARY KEY (entity_type, entity_id)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ca_address ON content_addresses(address)"
    )


# --- Address computation per level ---

def address_atoms(conn: sqlite3.Connection) -> dict[int, str]:
    """Compute addresses for all morpheme_atoms. Returns {atom_id: address}."""
    rows = conn.execute(
        "SELECT id, base_letter, diacritics FROM morpheme_atoms ORDER BY id"
    ).fetchall()
    addresses = {}
    for r in rows:
        canonical = _atom_canonical(r['base_letter'], r['diacritics'])
        addresses[r['id']] = _sha256(canonical)
    return addresses


def address_morpheme_types(conn: sqlite3.Connection, atom_addrs: dict[int, str]) -> dict[int, str]:
    """Compute addresses for all morpheme_types from atoms + feature IDs."""
    # Atom content per morpheme type
    atom_rows = conn.execute(
        "SELECT morpheme_type_id, id FROM morpheme_atoms ORDER BY morpheme_type_id, position"
    ).fetchall()
    mt_atoms: dict[int, list[str]] = {}
    for r in atom_rows:
        mt_atoms.setdefault(r['morpheme_type_id'], []).append(atom_addrs[r['id']])

    # Feature IDs per morpheme type
    feature_cols = [
        'root_id', 'lemma_id', 'pos_id', 'verb_form_id', 'voice_id',
        'mood_id', 'aspect_id', 'person_id', 'number_id', 'gender_id', 'case_value_id'
    ]
    col_list = ', '.join(feature_cols)
    feat_rows = conn.execute(f"SELECT id, {col_list} FROM morpheme_types").fetchall()

    mt_features: dict[int, str] = {}
    for r in feat_rows:
        parts = []
        for col in feature_cols:
            v = r[col]
            if v is not None:
                parts.append(f"{col}={v}")
        mt_features[r['id']] = '|'.join(parts)

    addresses = {}
    for mt_id, child_addrs in mt_atoms.items():
        atom_bytes = _sequence_canonical(child_addrs)
        feat_bytes = mt_features.get(mt_id, '').encode('ascii')
        addresses[mt_id] = _sha256(atom_bytes + b'#' + feat_bytes)
    return addresses


def address_word_types(conn: sqlite3.Connection, mt_addrs: dict[int, str]) -> dict[int, str]:
    """Compute addresses for all word_types from their ordered morpheme addresses."""
    rows = conn.execute(
        "SELECT word_type_id, morpheme_type_id FROM word_type_morphemes ORDER BY word_type_id, position"
    ).fetchall()

    wt_morphemes: dict[int, list[str]] = {}
    for r in rows:
        wt_morphemes.setdefault(r['word_type_id'], []).append(mt_addrs[r['morpheme_type_id']])

    addresses = {}
    for wt_id, child_addrs in wt_morphemes.items():
        addresses[wt_id] = _sha256(_sequence_canonical(child_addrs))
    return addresses


def address_word_instances(conn: sqlite3.Connection, wt_addrs: dict[int, str]) -> dict[str, str]:
    """Compute addresses for all word_instances: hash(word_type_address @ location)."""
    rows = conn.execute(
        "SELECT id, word_type_id, verse_surah, verse_ayah, word_index FROM word_instances"
    ).fetchall()

    addresses = {}
    for r in rows:
        wt_addr = wt_addrs.get(r['word_type_id'], '')
        location = f"{r['verse_surah']}:{r['verse_ayah']}:{r['word_index']}"
        canonical = wt_addr.encode('ascii') + b'@' + location.encode('ascii')
        addresses[r['id']] = _sha256(canonical)
    return addresses


def address_verses(conn: sqlite3.Connection, wi_addrs: dict[str, str]) -> dict[str, str]:
    """Compute addresses for all verses: hash of ordered word instance addresses."""
    rows = conn.execute(
        "SELECT id, verse_surah, verse_ayah, word_index FROM word_instances ORDER BY verse_surah, verse_ayah, word_index"
    ).fetchall()

    verse_instances: dict[str, list[str]] = {}
    for r in rows:
        key = f"{r['verse_surah']}:{r['verse_ayah']}"
        verse_instances.setdefault(key, []).append(wi_addrs[r['id']])

    addresses = {}
    for verse_key, child_addrs in verse_instances.items():
        addresses[verse_key] = _sha256(_sequence_canonical(child_addrs))
    return addresses


def address_entries(conn: sqlite3.Connection) -> dict[str, str]:
    """Compute addresses for all research entries.

    Address = hash(content | anchor_type | anchor_ids).
    This captures the core identity of the claim/research.
    """
    rows = conn.execute(
        "SELECT id, content, anchor_type, anchor_ids FROM entries"
    ).fetchall()
    
    addresses = {}
    for r in rows:
        # Canonical form for an entry statement
        content_part = (r['content'] or '').encode('utf-8')
        anchor_type = (r['anchor_type'] or '').encode('ascii')
        anchor_ids = (r['anchor_ids'] or '').encode('ascii')
        
        canonical = b'|'.join([content_part, anchor_type, anchor_ids])
        addresses[r['id']] = _sha256(canonical)
    return addresses


# --- Bulk store ---

def store_addresses(conn: sqlite3.Connection, entity_type: str, addresses: dict):
    """Bulk-insert addresses into content_addresses table."""
    data = [(entity_type, str(eid), addr) for eid, addr in addresses.items()]
    conn.executemany(
        "INSERT OR REPLACE INTO content_addresses (entity_type, entity_id, address) VALUES (?, ?, ?)",
        data
    )


# --- Full pipeline ---

def compute_all_addresses(conn: sqlite3.Connection) -> dict[str, int]:
    """Compute and store content addresses for the entire Quranic text + entries."""
    initialize_address_table(conn)

    # Bottom-up
    atom_addrs = address_atoms(conn)
    store_addresses(conn, 'atom', atom_addrs)

    mt_addrs = address_morpheme_types(conn, atom_addrs)
    store_addresses(conn, 'morpheme_type', mt_addrs)

    wt_addrs = address_word_types(conn, mt_addrs)
    store_addresses(conn, 'word_type', wt_addrs)

    wi_addrs = address_word_instances(conn, wt_addrs)
    store_addresses(conn, 'word_instance', wi_addrs)

    verse_addrs = address_verses(conn, wi_addrs)
    store_addresses(conn, 'verse', verse_addrs)

    entry_addrs = address_entries(conn)
    store_addresses(conn, 'entry', entry_addrs)

    conn.commit()

    return {
        'atoms': len(atom_addrs),
        'morpheme_types': len(mt_addrs),
        'word_types': len(wt_addrs),
        'word_instances': len(wi_addrs),
        'verses': len(verse_addrs),
        'entries': len(entry_addrs),
    }


# --- Lookup helpers ---

def get_address(conn: sqlite3.Connection, entity_type: str, entity_id: str) -> str | None:
    """Look up the content address for an entity."""
    row = conn.execute(
        "SELECT address FROM content_addresses WHERE entity_type = ? AND entity_id = ?",
        (entity_type, str(entity_id))
    ).fetchone()
    return row['address'] if row else None


def find_by_address(conn: sqlite3.Connection, address: str) -> list[dict]:
    """Find all entities with a given content address."""
    rows = conn.execute(
        "SELECT entity_type, entity_id FROM content_addresses WHERE address = ?",
        (address,)
    ).fetchall()
    return [dict(r) for r in rows]


def update_entry_address(conn: sqlite3.Connection, entry_id: str, content: str, anchor_type: str | None, anchor_ids: str | None) -> str:
    """Compute and store address for a single research entry."""
    content_part = (content or '').encode('utf-8')
    a_type = (anchor_type or '').encode('ascii')
    a_ids = (anchor_ids or '').encode('ascii')
    
    canonical = b'|'.join([content_part, a_type, a_ids])
    address = _sha256(canonical)
    
    conn.execute(
        "INSERT OR REPLACE INTO content_addresses (entity_type, entity_id, address) VALUES (?, ?, ?)",
        ('entry', str(entry_id), address)
    )
    return address
