import sqlite3
from pathlib import Path
DATA_DIR = Path("data")

kalima = sqlite3.connect(str(DATA_DIR / "kalima.db"))
qul = sqlite3.connect(str(DATA_DIR / "ayah-root.db" / "ayah-root.db"))

# Build lookup: root string -> first ID
# Take the first entry for each unique root string
cursor = kalima.cursor()
cursor.execute("SELECT id, lookup_key FROM features WHERE feature_type = 'root'")
root_to_id = {}
for id, key in cursor.fetchall():
    if key not in root_to_id:
        root_to_id[key] = id

print(f"Unique roots: {len(root_to_id)}")

matching = 0
mismatched = 0

# Compare using strings
for vk, in qul.execute("SELECT verse_key FROM roots").fetchall():
    surah, ayah = map(int, vk.split(":"))
    
    q_text = qul.execute("SELECT text FROM roots WHERE verse_key = ?", (vk,)).fetchone()[0]
    q_roots = set(q_text.split())
    
    # Get Kalima roots as strings (not IDs)
    k_strings = set()
    for root, in kalima.execute("""
        SELECT f.lookup_key
        FROM word_instances wi
        JOIN morpheme_types mt ON wi.word_type_id = mt.id
        JOIN features f ON mt.root_id = f.id
        WHERE f.feature_type = 'root' AND wi.verse_surah = ? AND wi.verse_ayah = ?
    """, (surah, ayah)).fetchall():
        k_strings.add(root)
    
    if q_roots == k_strings:
        matching += 1
    else:
        mismatched += 1

print(f"Matching: {matching}")
print(f"Mismatched: {mismatched}")