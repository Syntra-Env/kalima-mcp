import sqlite3, sys
from pathlib import Path
DATA_DIR = Path("data")
kalima = sqlite3.connect(str(DATA_DIR / "kalima.db"))
q = sqlite3.connect(str(DATA_DIR / "ayah-root.db" / "ayah-root.db"))

# Compare 1:1
q_text = q.execute("SELECT text FROM roots WHERE verse_key = '1:1'").fetchone()[0]
q_count = len(q_text.split())

k_count = kalima.execute("""
    SELECT COUNT(*)
    FROM word_instances wi
    JOIN morpheme_types mt ON wi.word_type_id = mt.id
    JOIN features f ON mt.root_id = f.id
    WHERE f.feature_type = 'root' AND wi.verse_surah = 1 AND wi.verse_ayah = 1
""").fetchone()[0]

sys.stdout.write(f"QUL: {q_count}, Kalima: {k_count}")
if q_count == k_count:
    sys.stdout.write(" - MATCH")
else:
    sys.stdout.write(" - NO MATCH")
sys.stdout.write("\n")