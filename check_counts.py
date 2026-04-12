import sqlite3
from pathlib import Path

DATA_DIR = Path("C:/Syntra/Kalima-mcp/data")
db = DATA_DIR / "kalima.db"
qul = DATA_DIR / "ayah-root.db" / "ayah-root.db"

conn = sqlite3.connect(str(db))
cursor = conn.cursor()

# Count words per verse in our DB
cursor.execute("""
    SELECT verse_surah, verse_ayah, COUNT(*) as cnt 
    FROM word_instances 
    GROUP BY verse_surah, verse_ayah
""")
our_counts = {}
for surah, ayah, cnt in cursor.fetchall():
    our_counts[f"{surah}:{ayah}"] = cnt

# Count roots per verse in QUL
qul_conn = sqlite3.connect(str(qul))
qul_counts = {}
for vk, text in qul_conn.execute("SELECT verse_key, text FROM roots").fetchall():
    qul_counts[vk] = len(text.split())

# Compare counts
matching = 0
not_matching = 0
for vk, qcnt in qul_counts.items():
    ocnt = our_counts.get(vk, 0)
    if qcnt == ocnt:
        matching += 1
    else:
        not_matching += 1

print(f"Verses with matching counts: {matching}")
print(f"Verses with different counts: {not_matching}")

# Show some mismatches
print("\nSample mismatches:")
i = 0
for vk, qcnt in qul_counts.items():
    if our_counts.get(vk, 0) != qcnt and i < 5:
        print(f"  {vk}: QUL={qcnt}, ours={our_counts.get(vk, 0)}")
        i += 1

conn.close()
qul_conn.close()