import sqlite3
from pathlib import Path

DATA_DIR = Path("C:/Syntra/Kalima-mcp/data")
db = DATA_DIR / "kalima.db"

conn = sqlite3.connect(str(db))
cursor = conn.cursor()

# 1. Get unique roots from QUL verse_roots table
qul_roots = set()
for roots, in cursor.execute("SELECT roots FROM verse_roots").fetchall():
    for r in roots.split():
        qul_roots.add(r)
print(f"QUL unique roots: {len(qul_roots)}")

# 2. Get unique roots we're using from QPC
qpc_roots = set()
cursor.execute("""
    SELECT DISTINCT f.lookup_key 
    FROM morpheme_types mt
    JOIN features f ON mt.root_id = f.id
    WHERE f.feature_type = 'root'
""")
qpc_roots = {r[0] for r in cursor.fetchall()}
print(f"QPC used unique roots: {len(qpc_roots)}")

# 3. Compare
only_qul = qul_roots - qpc_roots
only_qpc = qpc_roots - qul_roots

print(f"Only in QUL (new): {len(only_qul)}")
print(f"Only in QPC (not in QUL): {len(only_qpc)}")

# Show first few only in QUL
print(f"\nFirst 10 only in QUL:")
for r in list(only_qul)[:10]:
    print(f"  {r}")

conn.close()