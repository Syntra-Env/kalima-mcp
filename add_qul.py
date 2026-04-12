import sqlite3
from pathlib import Path

DATA_DIR = Path("C:/Syntra/Kalima-mcp/data")
db = DATA_DIR / "kalima.db"
qul = DATA_DIR / "ayah-root.db" / "ayah-root.db"

conn = sqlite3.connect(str(db))
cursor = conn.cursor()

# Get roots
cursor.execute("SELECT id, lookup_key FROM features WHERE feature_type = 'root'")
root_lookup = {k: v for v, k in cursor.fetchall()}

# Get QUL unique roots
qul_roots = set()
for text, in sqlite3.connect(str(qul)).execute("SELECT text FROM roots").fetchall():
    for r in text.split():
        qul_roots.add(r)

print(f"QUL unique roots: {len(qul_roots)}")

# Add missing QUL roots to features
new_roots = qul_roots - set(root_lookup.keys())
print(f"New roots from QUL: {len(new_roots)}")

for r in new_roots:
    cursor.execute(
        "INSERT OR IGNORE INTO features (feature_type, category, lookup_key) VALUES (?, ?, ?)",
        ('root', None, r)
    )

conn.commit()

# Rebuild lookup
cursor.execute("SELECT id, lookup_key FROM features WHERE feature_type = 'root'")
root_lookup = {k: v for v, k in cursor.fetchall()}
print(f"Total roots now: {len(root_lookup)}")

conn.close()