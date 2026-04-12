import sqlite3
from pathlib import Path
DATA_DIR = Path("data")

kalima = sqlite3.connect(str(DATA_DIR / "kalima.db"))
qul = sqlite3.connect(str(DATA_DIR / "ayah-root.db" / "ayah-root.db"))

# Just count differences
for vk, in qul.execute("SELECT verse_key FROM roots LIMIT 20").fetchall():
    surah, ayah = map(int, vk.split(":"))
    
    q_text = qul.execute("SELECT text FROM roots WHERE verse_key = ?", (vk,)).fetchone()[0]
    q_count = len(q_text.split())
    
    k_count = kalima.execute("""
        SELECT COUNT(*)
        FROM word_instances wi
        JOIN morpheme_types mt ON wi.word_type_id = mt.id
        JOIN features f ON mt.root_id = f.id
        WHERE f.feature_type = 'root' AND wi.verse_surah = ? AND wi.verse_ayah = ?
    """, (surah, ayah)).fetchone()[0]
    
    if q_count != k_count:
        print(f"{vk}: QUL={q_count}, Kal={k_count}, diff={k_count-q_count}")