import sqlite3
from pathlib import Path
DATA_DIR = Path("data")

kalima = sqlite3.connect(str(DATA_DIR / "kalima.db"))
qul = sqlite3.connect(str(DATA_DIR / "ayah-root.db" / "ayah-root.db"))

# Count matching
matching = 0
for vk, in qul.execute("SELECT verse_key FROM roots").fetchall():
    surah, ayah = map(int, vk.split(":"))
    
    q_count = len(qul.execute("SELECT text FROM roots WHERE verse_key = ?", (vk,)).fetchone()[0].split())
    k_count = kalima.execute("""
        SELECT COUNT(*) FROM word_instances wi
        JOIN morpheme_types mt ON wi.word_type_id = mt.id
        JOIN features f ON mt.root_id = f.id
        WHERE f.feature_type = 'root' AND wi.verse_surah = ? AND wi.verse_ayah = ?
    """, (surah, ayah)).fetchone()[0]
    
    if q_count == k_count:
        matching += 1

print(f"Matching verses: {matching}")

# Total
q_total = sum(len(r[0].split()) for r in qul.execute("SELECT text FROM roots").fetchall())
k_total = kalima.execute("SELECT COUNT(*) FROM morpheme_types WHERE root_id IS NOT NULL").fetchone()[0]
print(f"QUL roots total: {q_total}")
print(f"Kalima roots total: {k_total}")

kalima.close()
qul.close()