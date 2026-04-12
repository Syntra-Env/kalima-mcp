import sqlite3, re
from pathlib import Path

DATA_DIR = Path("C:/Syntra/Kalima-mcp/data")
db = DATA_DIR / "kalima.db"
morph = DATA_DIR / "quran-morphology.txt"

conn = sqlite3.connect(str(db))
cursor = conn.cursor()

# Get roots
cursor.execute("SELECT id, lookup_key FROM features WHERE feature_type = 'root'")
root_lookup = {k: v for v, k in cursor.fetchall()}

# Build text -> root mapping (choosing most common IF multiple)
# From source: we need text -> most_common_root
text_to_root = {}
text_counts = {}

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
        
        text = parts[1]
        
        if text not in text_counts:
            text_counts[text] = {}
        if root not in text_counts[text]:
            text_counts[text][root] = 0
        text_counts[text][root] += 1

# Now pick most common root for each text
for text, roots in text_counts.items():
    if roots:
        # Get most common
        most_common = max(roots.keys(), key=lambda r: roots[r])
        text_to_root[text] = most_common

print(f"Mapped: {len(text_to_root)} morphemes")

# Update DB with MATCHING texts that have ID > 0
cursor.execute("UPDATE morpheme_types SET root_id = NULL")

updated = 0
for text, root in text_to_root.items():
    if root in root_lookup:
        # Find matching morpheme_types with this text and no root
        cursor.execute("""
            UPDATE morpheme_types 
            SET root_id = ? 
            WHERE uthmani_text = ? AND root_id IS NULL
        """, (root_lookup[root], text))
        updated += cursor.rowcount

conn.commit()
print(f"Updated: {updated}")

cursor.execute("SELECT COUNT(*) FROM morpheme_types WHERE root_id IS NOT NULL")
print(f"Final: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(DISTINCT root_id) FROM morpheme_types WHERE root_id IS NOT NULL")
print(f"Unique roots: {cursor.fetchone()[0]}")

conn.close()