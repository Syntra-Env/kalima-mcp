
import sys
import os
sys.path.append(os.getcwd())
from src.db import get_connection
from src.utils.uor_ring import hex_to_int, get_incompatibility
from src.utils.addressing import get_address

def analyze_interpretive_tension():
    conn = get_connection()
    # 1. Select the specific entry
    query = "SELECT address, content FROM holonomic_entries WHERE content LIKE '%Iblis as Manifold Perturbation%' LIMIT 1"
    entry = conn.execute(query).fetchone()
    
    # 2. Get the anchor verse address
    anchor_addr = get_address(conn, 'verse', '15:31')
    
    if entry and anchor_addr:
        x = hex_to_int(entry['address'])
        y = hex_to_int(anchor_addr)
        
        # d_Delta = |d_Ring - d_Hamming|
        tension = get_incompatibility(x, y)
        
        print(f"ANALYSIS OF INTERPRETIVE DOCKING")
        print(f"==============================")
        print(f"Interpretation: {entry['content'][:100]}...")
        print(f"Anchor Verse:   15:31")
        print(f"Geometric Tension (d_Delta): {tension:.6f}")
        print(f"\nInterpretive Stability Classification:")
        
        if tension < 0.1:
            print(">> HOLONOMIC RESONANCE: This interpretation is mathematically 'quiet'. It aligns deeply with the underlying structure.")
        elif tension < 0.25:
            print(">> STEADY COUPLING: This interpretation provides a stable new perspective without distorting the field.")
        else:
            print(">> GAUGE PERTURBATION: This is a high-energy interpretation. It actively reconfigures the manifold at this coordinate.")

if __name__ == "__main__":
    analyze_interpretive_tension()
