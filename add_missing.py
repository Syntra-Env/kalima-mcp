import sqlite3
from pathlib import Path

DATA_DIR = Path("C:/Syntra/Kalima-mcp/data")
db = DATA_DIR / "kalima.db"

conn = sqlite3.connect(str(db))
cursor = conn.cursor()

# Get roots currently in features table
cursor.execute("SELECT id, lookup_key FROM features WHERE feature_type = 'root'")
existing = {r[1] for r in cursor.fetchall()}
print(f"Current roots in features: {len(existing)}")

# Get unique roots from QUL verse_roots
qul_roots = set()
for roots, in cursor.execute("SELECT roots FROM verse_roots").fetchall():
    for r in roots.split():
        qul_roots.add(r)
print(f"QUL unique roots: {len(qul_roots)}")

# Find new ones to add
new_roots = qul_roots - existing
print(f"New roots to add: {len(new_roots)}")

# Add to features table
for r in new_roots:
    cursor.execute("""
        INSERT OR IGNORE INTO features (feature_type, category, lookup_key)
        VALUES ('root', NULL, ?)
    """, (r,))

conn.commit()

# Update count
cursor.execute("SELECT COUNT(*) FROM features WHERE feature_type = 'root'")
print(f"Final roots in features: {cursor.fetchone()[0]}")

conn.close()