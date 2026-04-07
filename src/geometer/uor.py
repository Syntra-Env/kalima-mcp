"""
UOR Ring Substrate: Z/(2^256)Z Arithmetic and Dihedral Symmetry.

This module wraps the canonical PRISM implementation for 256-bit (Q31) operations.
All arithmetic is derived from the PRISM engine which IS the specification.
"""

from .prism import UOR

# PRISM Quantum 31 = 32 bytes = 256 bits
# This is the ring used for SHA-256 content addressing
Q256 = UOR(quantum=31)

# Expose the engine for direct PRISM operations
engine = Q256

# Ring parameters
BITS = Q256.bits
WIDTH = Q256.width
CYCLE = Q256.cycle
MASK = Q256._mask

def hex_to_int(h: str) -> int:
    """Convert hex address to ring element."""
    return int(h, 16) & MASK

def int_to_hex(i: int) -> str:
    """Convert ring element to hex address."""
    return hex(i & MASK)[2:].zfill(64)

def _to_bytes(n: int) -> tuple:
    """Convert integer to PRISM byte tuple."""
    return Q256._to_bytes(n)

def _from_bytes(b: tuple) -> int:
    """Convert PRISM byte tuple to integer."""
    return Q256._from_bytes(b)

# --- Dihedral Group Generators (delegated to PRISM) ---

def bnot(x: int) -> int:
    """Bitwise NOT generator: ~x mod 2^256."""
    return _from_bytes(Q256.bnot(_to_bytes(x)))

def neg(x: int) -> int:
    """Arithmetic negation generator: -x mod 2^256."""
    return _from_bytes(Q256.neg(_to_bytes(x)))

def succ(x: int) -> int:
    """Successor operation: x + 1 mod 2^256 (derived: neg(bnot(x)))."""
    return _from_bytes(Q256.succ(_to_bytes(x)))

def pred(x: int) -> int:
    """Predecessor operation: x - 1 mod 2^256 (derived: bnot(neg(x)))."""
    return _from_bytes(Q256.pred(_to_bytes(x)))

def xor(x: int, y: int) -> int:
    """XOR operation: x ^ y mod 2^256."""
    return _from_bytes(Q256.xor(_to_bytes(x), _to_bytes(y)))

def band(x: int, y: int) -> int:
    """AND operation: x & y mod 2^256."""
    return _from_bytes(Q256.band(_to_bytes(x), _to_bytes(y)))

def bor(x: int, y: int) -> int:
    """OR operation: x | y mod 2^256."""
    return _from_bytes(Q256.bor(_to_bytes(x), _to_bytes(y)))

def verify_uor_identity(x: int) -> bool:
    """Verify the core PRISM identity: neg(bnot(x)) == succ(x)."""
    return neg(bnot(x)) == succ(x)

# --- UOR Metrics ---

def dist_hamming(x: int, y: int) -> int:
    """Hamming distance d_H: number of differing bits."""
    return bin(x ^ y).count('1')

def dist_ring(x: int, y: int) -> int:
    """Ring distance d_R: cyclic arithmetic distance."""
    diff = (x - y) & MASK
    return min(diff, (CYCLE - diff))

def get_incompatibility(x: int, y: int) -> float:
    """Incompatibility metric d_Δ = |d_R - d_H| normalized."""
    dh = dist_hamming(x, y) / 256.0
    dr = dist_ring(x, y) / (CYCLE // 2)
    return abs(dr - dh)

def get_dihedral_orbit(x: int) -> dict:
    """Calculate the 4-element dihedral equivalence class (The 'Atom')."""
    return {
        "identity": x,
        "neg": neg(x),
        "bnot": bnot(x),
        "succ_bnot": neg(bnot(x))
    }

def decompose_fibers(x: int) -> list:
    """Z/2Z fibration of ring elements into 256 binary fibers."""
    return [(x >> i) & 1 for i in range(256)]

def get_stratum(x: int) -> int:
    """Stratum: sum of popcounts across all bytes."""
    total = 0
    for i in range(WIDTH):
        byte = (x >> (8 * (WIDTH - 1 - i))) & 0xFF
        total += byte.bit_count() if hasattr(byte, 'bit_count') else bin(byte).count('1')
    return total

def get_spectrum(x: int) -> list:
    """Spectrum: basis elements per byte position."""
    b = _to_bytes(x)
    result = []
    for byte in b:
        result.append([i for i in range(8) if byte & (1 << i)])
    return result

def get_triad(x: int) -> dict:
    """Complete triadic coordinates: datum, stratum, spectrum."""
    b = _to_bytes(x)
    triad = Q256.triad(b)
    return {
        "datum": triad.datum,
        "stratum": triad.stratum,
        "spectrum": triad.spectrum,
        "total_stratum": triad.total_stratum
    }

def correlate(x: int, y: int) -> dict:
    """Correlate two values: fidelity and total difference."""
    return Q256.correlate(x, y)

# --- PRISM Derivation Support ---

def make_term(operation: str, *operands: int) -> 'Term':
    """Create a PRISM term from integers."""
    from .prism import Term
    byte_operands = [_to_bytes(op) for op in operands]
    term = Q256.make_term(operation, *byte_operands)
    return term

def derive(operation: str, *operands: int) -> 'Derivation':
    """Create a derivation (certificate) for an operation."""
    term = make_term(operation, *operands)
    return Q256.derive(term)

# --- Verify PRISM Coherence ---
# Run this to verify the engine before use
def verify() -> bool:
    """Verify PRISM coherence at Q31 (256-bit)."""
    return Q256.verify()

# Run verification on module load
verify()
