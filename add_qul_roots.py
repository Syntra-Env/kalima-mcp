import sqlite3
from pathlib import Path

DB_PATH = Path("data/kalima.db")
QUL_PATH = Path("data/ayah-root.db/ayah-root.db")

conn = sqlite3.connect(str(DB_PATH))
qul = sqlite3.connect(str(QUL_PATH))

# Get word instance mapping
print("Building word index...")
cursor = conn.cursor()
cursor.execute("SELECT verse_surah, verse_ayah, word_index, word_type_id FROM word_instances")
loc_to_wtid = {(s, a, w): t for s, a, w, t in cursor.fetchall()}
print(f"Words: {len(loc_to_wtid)}")

# Get existing roots in features
cursor.execute("SELECT id, lookup_key FROM features WHERE feature_type = 'root'")
root_lookup = {k: v for v, k in cursor.fetchall()}
print(f"Roots in features: {len(root_lookup)}")

# Add missing QUL roots to features
print("Checking QUL roots...")
missing_roots = set()
for text, in qul.execute("SELECT text FROM roots").fetchall():
    for root in text.split():
        if root and root not in root_lookup:
            missing_roots.add(root)

print(f"New roots: {len(missing_roots)}")

# Add to features
if missing_roots:
    for root in missing_roots:
        cursor.execute(
            "INSERT OR IGNORE INTO features (feature_type, category, lookup_key) VALUES (?, ?, ?)",
            ('root', None, root)
        )
    conn.commit()
    cursor.execute("SELECT id, lookup_key FROM features WHERE feature_type = 'root'")
    root_lookup = {k: v for v, k in cursor.fetchall()}
    print(f"Total roots: {len(root_lookup)}")

# Now fill gaps from QUL - for each word without root, try to get from QUL
print("Filling gaps from QUL...")
filled = 0

# Build uthmani_text -> root for words that DO have roots
cursor.execute("""
    SELECT uthmani_text, root_id FROM morpheme_types 
    WHERE root_id IS NOT NULL AND uthmani_text IS NOT NULL
""")
text_to_root = {}
for text, rid in cursor.fetchall():
    if text not in text_to_root:
        text_to_root[text] = set()
    text_to_root[text].add(rid)

print(f"Text mappings: {len(text_to_root)}")

# QUL word-level: need to parse verse text to get word->root mapping
# This is harder - QUL only has verse-level roots, not word-level

# Alternative: for words without roots, try text match ONLY where unique
cursor.execute("""
    SELECT id, uthmani_text FROM morpheme_types 
    WHERE root_id IS NULL AND uthmani_text IS NOT NULL
""")
missing = cursor.fetchall()
print(f"Words needing roots: {len(missing)}")

for mt_id, text in missing:
    if text in text_to_root:
        roots = text_to_root[text]
        if len(roots) == 1:
            cursor.execute(
                "UPDATE morpheme_types SET root_id = ? WHERE id = ?",
                (list(roots)[0], mt_id)
            )
            filled += 1

conn.commit()
print(f"Filled: {filled}")

# Stats
cursor.execute("SELECT COUNT(*) FROM morpheme_types WHERE root_id IS NOT NULL")
print(f"Final: {cursor.fetchone()[0]}")

conn.close()
qul.close()