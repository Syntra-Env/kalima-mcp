import sqlite3
from pathlib import Path

DATA_DIR = Path("C:/Syntra/Kalima-mcp/data")
db = DATA_DIR / "kalima.db"
qul = DATA_DIR / "ayah-root.db" / "ayah-root.db"

conn = sqlite3.connect(str(db))
qul_conn = sqlite3.connect(str(qul))
cursor = conn.cursor()

# Get roots in features
cursor.execute("SELECT id, lookup_key FROM features WHERE feature_type = 'root'")
root_lookup = {k: v for v, k in cursor.fetchall()}

# Reset
cursor.execute("UPDATE morpheme_types SET root_id = NULL")

# Try matching: for each verse where QUL word count == our word count
matched = 0
filled = 0

# Get QUL data
qul_verses = {}
for vk, text in qul_conn.execute("SELECT verse_key, text FROM roots").fetchall():
    qul_verses[vk] = text.split()

# Our words per verse
cursor.execute("SELECT verse_surah, verse_ayah, word_index FROM word_instances")
verse_words = {}
for surah, ayah, widx in cursor.fetchall():
    key = f"{surah}:{ayah}"
    if key not in verse_words:
        verse_words[key] = []
    verse_words[key].append(widx)

# Try to match verses
for vk, roots in qul_verses.items():
    surah, ayah = map(int, vk.split(':'))
    
    # Get words in this verse
    words = verse_words.get(f"{surah}:{ayah}", [])
    
    # If same count, try position matching
    if len(words) == len(roots):
        for i, widx in enumerate(words):
            root = roots[i]
            root_id = root_lookup.get(root)
            if root_id:
                # Find the morpheme at this word position
                cursor.execute("""
                    UPDATE morpheme_types SET root_id = ?
                    WHERE id = (
                        SELECT word_type_id FROM word_instances 
                        WHERE verse_surah = ? AND verse_ayah = ? AND word_index = ?
                    )
                """, (root_id, surah, ayah, widx))
                filled += cursor.rowcount
    
    matched += 1

conn.commit()
print(f"Filled: {filled}")
print(f"Final: {conn.execute('SELECT COUNT(*) FROM morpheme_types WHERE root_id IS NOT NULL').fetchone()[0]}")

conn.close()
qul_conn.close()