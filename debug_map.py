import re, sqlite3
from pathlib import Path

morph = Path("C:/Syntra/Kalima-mcp/data/quran-morphology.txt")
db = Path("C:/Syntra/Kalima-mcp/data/kalima.db")

# Build text->root from morphology - count only
text_to_root = {}
with open(str(morph), 'r', encoding='utf-8') as f:
    for line in f:
        if 'ROOT:' not in line:
            continue
        m = re.search(r'ROOT:(\w+)', line)
        root = m.group(1) if m else None
        parts = line.strip().split('\t')
        if len(parts) >= 2:
            text = parts[1]
            if text not in text_to_root:
                text_to_root[text] = set()
            text_to_root[text].add(root)

# Check coverage
unique_texts = len(text_to_root)
single_root = sum(1 for r in text_to_root.values() if len(r) == 1)
multi_root = sum(1 for r in text_to_root.values() if len(r) > 1)

print(f"Unique texts in morph file: {unique_texts}")
print(f"With single root: {single_root}")
print(f"With multiple roots: {multi_root}")

# Check DB coverage
conn = sqlite3.connect(str(db))
db_count = conn.execute("SELECT COUNT(DISTINCT uthmani_text) FROM morpheme_types").fetchone()[0]
print(f"Unique texts in DB: {db_count}")

# Check overlap
db_texts = set(r[0] for r in conn.execute("SELECT uthmani_text FROM morpheme_types").fetchall())
morph_texts = set(text_to_root.keys())
overlap = db_texts & morph_texts
print(f"Overlap: {len(overlap)}")

# Check how many have unique mappings
usable = sum(1 for t in overlap if len(text_to_root.get(t, [])) == 1)
print(f"Usable (single root): {usable}")

conn.close()