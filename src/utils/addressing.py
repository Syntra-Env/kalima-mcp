"""UOR content addressing and Holonomic Vector Engine.

Implements Multi-Layer awareness informed by HUFD (Curvature/Resonance) 
and UOR (Bottom-Up Content Identity).
"""

import hashlib
import sqlite3

def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _atom_canonical(base_letter: str, diacritics: str) -> bytes:
    return (base_letter or '').encode('utf-8') + (diacritics or '').encode('utf-8')

def _sequence_canonical(child_addresses: list[str]) -> bytes:
    return b'|'.join(a.encode('ascii') for a in child_addresses)

# --- Table setup ---

def initialize_address_table(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS content_addresses (
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            address TEXT NOT NULL,
            PRIMARY KEY (entity_type, entity_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ca_address ON content_addresses(address)")

# --- Vector Engine ---

def get_holonomic_vector(conn: sqlite3.Connection, word_instance_id: str) -> dict:
    """Compute the multi-layer Holonomic Vector (Identity Stack) for a word.
    
    Layers:
    - Basis (Root): The source field A_root.
    - Gauge (Morpheme): The manifested state H_mu.
    - Identity (Word Type): The localized invariant.
    - Charge (Features): The grammatical specificities.
    """
    row = conn.execute("""
        SELECT 
            wi.word_type_id,
            wtm.morpheme_type_id,
            mt.root_id,
            mt.id as mt_id
        FROM word_instances wi
        JOIN word_type_morphemes wtm ON wtm.word_type_id = wi.word_type_id
        JOIN morpheme_types mt ON mt.id = wtm.morpheme_type_id
        WHERE wi.id = ?
    """, (word_instance_id,)).fetchone()
    
    if not row: return {}

    # 1. Fetch addresses
    root_addr = conn.execute(
        "SELECT address FROM content_addresses WHERE entity_type='root' AND entity_id=?", 
        (str(row['root_id']),)).fetchone()
    
    mt_addr = conn.execute(
        "SELECT address FROM content_addresses WHERE entity_type='morpheme_type' AND entity_id=?", 
        (str(row['mt_id']),)).fetchone()
        
    wt_addr = conn.execute(
        "SELECT address FROM content_addresses WHERE entity_type='word_type' AND entity_id=?", 
        (str(row['word_type_id']),)).fetchone()

    # 2. Extract Charge (Features)
    feat_cols = [
        'pos_id', 'verb_form_id', 'voice_id', 'mood_id', 'aspect_id', 
        'person_id', 'number_id', 'gender_id', 'case_value_id'
    ]
    f_row = conn.execute(f"SELECT {', '.join(feat_cols)} FROM morpheme_types WHERE id = ?", (row['mt_id'],)).fetchone()
    charge = "|".join([f"{c}={f_row[c]}" for c in feat_cols if f_row[c] is not None])

    return {
        "instance_id": word_instance_id,
        "root_addr": root_addr[0] if root_addr else None,
        "morpheme_addr": mt_addr[0] if mt_addr else None,
        "word_type_addr": wt_addr[0] if wt_addr else None,
        "charge": charge
    }

# --- Legacy addressing functions (kept for background sync) ---

def get_address(conn: sqlite3.Connection, entity_type: str, entity_id: str) -> str | None:
    row = conn.execute("SELECT address FROM content_addresses WHERE entity_type=? AND entity_id=?", (entity_type, str(entity_id))).fetchone()
    return row[0] if row else None

def find_by_address(conn: sqlite3.Connection, address: str) -> list[dict]:
    rows = conn.execute("SELECT entity_type, entity_id FROM content_addresses WHERE address=?", (address,)).fetchall()
    return [dict(r) for r in rows]
