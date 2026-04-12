import sqlite3
from pathlib import Path
DATA_DIR = Path("data")

kalima = sqlite3.connect(str(DATA_DIR / "kalima.db"))
qul = sqlite3.connect(str(DATA_DIR / "ayah-root.db" / "ayah-root.db"))

matching = 0
mismatched = 0

for vk, in qul.execute("SELECT verse_key FROM roots").fetchall():
    surah, ayah = map(int, vk.split(":"))
    
    # QUL roots
    q_text = qul.execute("SELECT text FROM roots WHERE verse_key = ?", (vk,)).fetchone()[0]
    q_set = set(q_text.split())
    
    # Kalima roots
    k_set = set()
    for root, in kalima.execute("""
        SELECT f.lookup_key
        FROM word_instances wi
        JOIN morpheme_types mt ON wi.word_type_id = mt.id
        JOIN features f ON mt.root_id = f.id
        WHERE f.feature_type = 'root' AND wi.verse_surah = ? AND wi.verse_ayah = ?
    """, (surah, ayah)).fetchall():
        k_set.add(root)
    
    if q_set == k_set:
        matching += 1
    else:
        mismatched += 1

print(f"Matching: {matching}")
print(f"Mismatched: {mismatched}")