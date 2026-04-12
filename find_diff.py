import sqlite3
from pathlib import Path
DATA_DIR = Path("data")

kalima = sqlite3.connect(str(DATA_DIR / "kalima.db"))
qul = sqlite3.connect(str(DATA_DIR / "ayah-root.db" / "ayah-root.db"))

# Find first mismatched verse
for vk, in qul.execute("SELECT verse_key FROM roots").fetchall():
    surah, ayah = map(int, vk.split(":"))
    
    q_text = qul.execute("SELECT text FROM roots WHERE verse_key = ?", (vk,)).fetchone()[0]
    q_set = set(q_text.split())
    
    k_set = set()
    for root, in kalima.execute("""
        SELECT f.lookup_key
        FROM word_instances wi
        JOIN morpheme_types mt ON wi.word_type_id = mt.id
        JOIN features f ON mt.root_id = f.id
        WHERE f.feature_type = 'root' AND wi.verse_surah = ? AND wi.verse_ayah = ?
    """, (surah, ayah)).fetchall():
        k_set.add(root)
    
    if q_set != k_set:
        print(f"First mismatch: {vk}")
        print(f"  QUL count: {len(q_set)}")
        print(f"  Kalima count: {len(k_set)}")
        
        # Get first few differences
        only_q = q_set - k_set
        only_k = k_set - q_set
        
        if only_q:
            ids = []
            for r in list(only_q):
                f = kalima.execute("SELECT id FROM features WHERE lookup_key = ?", (r,)).fetchone()
                ids.append(f[0] if f else 'N')
            print(f"  ONLY QUL (ids): {ids}")
        
        if only_k:
            ids = []
            for r in list(only_k)[:5]:
                f = kalima.execute("SELECT id FROM features WHERE lookup_key = ?", (r,)).fetchone()
                ids.append(f[0] if f else 'N')
            print(f"  ONLY Kal (ids): {ids}")
        
        break