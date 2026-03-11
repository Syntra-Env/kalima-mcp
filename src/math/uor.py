"""UOR Ring Substrate: Z/(2^256)Z Arithmetic and Dihedral Symmetry.

Implements the mathematical foundation for UOR content addressing 
as specified in the Harlow/Charlton framework.
"""

import numpy as np

# Ring size for SHA-256 (256 bits)
MOD = 2**256
MASK = MOD - 1

def hex_to_int(h: str) -> int:
    """Convert hex address to ring element."""
    return int(h, 16) & MASK

def int_to_hex(i: int) -> str:
    """Convert ring element to hex address."""
    return hex(i & MASK)[2:].zfill(64)

# --- Dihedral Group Generators ---

def bnot(x: int) -> int:
    """Bitwise NOT generator: ~x mod 2^n."""
    return (~x) & MASK

def neg(x: int) -> int:
    """Arithmetic negation generator: -x mod 2^n."""
    return (-x) & MASK

def succ(x: int) -> int:
    """Successor operation: x + 1 mod 2^n."""
    return (x + 1) & MASK

def verify_uor_identity(x: int) -> bool:
    """Verify the core UOR identity: neg(bnot(x)) == succ(x)."""
    return neg(bnot(x)) == succ(x)

# --- UOR Metrics ---

def dist_hamming(x: int, y: int) -> int:
    """Hamming distance d_H: number of differing bits."""
    return bin(x ^ y).count('1')

def dist_ring(x: int, y: int) -> int:
    """Ring distance d_R: cyclic arithmetic distance."""
    diff = (x - y) & MASK
    return min(diff, (MOD - diff))

def get_incompatibility(x: int, y: int) -> float:
    """Incompatibility metric d_Δ = |d_R - d_H| normalized."""
    dh = dist_hamming(x, y) / 256.0
    dr = dist_ring(x, y) / (MOD // 2)
    return abs(dr - dh)

def get_dihedral_orbit(x: int) -> dict[str, int]:
    """Calculate the 4-element dihedral equivalence class (The 'Atom')."""
    return {
        "identity": x,
        "neg": neg(x),
        "bnot": bnot(x),
        "succ_bnot": neg(bnot(x))
    }

def decompose_fibers(x: int) -> list[int]:
    """Z/2Z fibration of ring elements into 256 binary fibers (P3.3)."""
    return [(x >> i) & 1 for i in range(256)]

def get_stratum(x: int) -> int:
    """Stratum v_2(x): 2-adic valuation as stratification (P3.3)."""
    if x == 0: return 256
    return (x & -x).bit_length() - 1
