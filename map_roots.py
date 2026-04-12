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

# Build text -> root from quran-morphology.txt
# Format: surah:ayah:word:seg TAB text TAB pos ...
text_to_root = {}

with open(str(morph), 'r', encoding='utf-8') as f:
    for line in f:
        if 'ROOT:' not in line:
            continue
        
        match = re.search(r'ROOT:(\w+)', line)
        if not match:
            continue
        root = match.group(1)
        
        parts = line.strip().split('\t')
        if len(parts) < 2:
            continue
        
        text = parts[1]  # This is the morpheme text
        
        if text not in text_to_root:
            text_to_root[text] = set()
        text_to_root[text].add(root)

print(f"Unique morphemes in quran-morphology: {len(text_to_root)}")

# Check morpheme_types
cursor.execute("SELECT COUNT(*) FROM morpheme_types")
print(f"Morpheme types in db: {cursor.fetchone()[0]}")

# Map ONLY where text has EXACTLY ONE root (verified unique)
cursor.execute("UPDATE morpheme_types SET root_id = NULL")

updated = 0
for text, roots in text_to_root.items():
    if len(roots) == 1:
        root = list(roots)[0]
        root_id = root_lookup.get(root)
        if root_id:
            # Update by matching uthmani_text
            cursor.execute("""
                UPDATE morpheme_types 
                SET root_id = ? 
                WHERE uthmani_text = ? AND root_id IS NULL
            """, (root_id, text))
            if cursor.rowcount > 0:
                updated += cursor.rowcount

conn.commit()
print(f"Updated: {updated}")

cursor.execute("SELECT COUNT(*) FROM morpheme_types WHERE root_id IS NOT NULL")
print(f"Final with roots: {cursor.fetchone()[0]}")

conn.close()