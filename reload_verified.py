import sqlite3
import re
from pathlib import Path

DATA_DIR = Path("data")
db = DATA_DIR / "kalima.db"
morph = DATA_DIR / "quran-morphology.txt"

conn = sqlite3.connect(str(db))
cursor = conn.cursor()

# Get roots
cursor.execute("SELECT id, lookup_key FROM features WHERE feature_type = 'root'")
root_lookup = {k: v for v, k in cursor.fetchall()}
print(f"Roots in db: {len(root_lookup)}")

# Parse morphology and map uthmani_text -> root (for full words only)
text_to_root = {}

with open(str(morph), 'r', encoding='utf-8') as f:
    for line in f:
        if 'ROOT:' not in line:
            continue
        
        match = re.search(r'ROOT:(\w+)', line)
        root = match.group(1) if match else None
        
        if not root:
            continue
        
        parts = line.strip().split('\t')
        if len(parts) < 2:
            continue
        
        # Get the actual word text (column 1)
        word_text = parts[1]
        
        if word_text not in text_to_root:
            text_to_root[word_text] = set()
        text_to_root[word_text].add(root)

print(f"Words mapped: {len(text_to_root)}")

# Keep ONLY texts with EXACTLY ONE root (verified unique)
cursor.execute("UPDATE morpheme_types SET root_id = NULL")

updated = 0
for text, roots in text_to_root.items():
    if len(roots) == 1:
        root = list(roots)[0]
        root_id = root_lookup.get(root)
        if root_id:
            cursor.execute("""
                UPDATE morpheme_types 
                SET root_id = ? 
                WHERE uthmani_text = ? AND root_id IS NULL
            """, (root_id, text))
            updated += cursor.rowcount

conn.commit()
print(f"Updated (unique): {updated}")

cursor.execute("SELECT COUNT(*) FROM morpheme_types WHERE root_id IS NOT NULL")
print(f"Final: {cursor.fetchone()[0]}")

conn.close()