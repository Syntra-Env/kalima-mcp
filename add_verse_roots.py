import sqlite3
from pathlib import Path

DATA_DIR = Path("C:/Syntra/Kalima-mcp/data")
db = DATA_DIR / "kalima.db"
qul = DATA_DIR / "ayah-root.db" / "ayah-root.db"

conn = sqlite3.connect(str(db))
cursor = conn.cursor()

# Create verse_roots table in kalima.db
cursor.execute("""
    CREATE TABLE IF NOT EXISTS verse_roots (
        surah INTEGER NOT NULL,
        ayah INTEGER NOT NULL,
        roots TEXT NOT NULL,
        PRIMARY KEY (surah, ayah)
    )
""")

# Load QUL data
qul_conn = sqlite3.connect(str(qul))
for vk, text in qul_conn.execute("SELECT verse_key, text FROM roots").fetchall():
    surah, ayah = map(int, vk.split(':'))
    cursor.execute(
        "INSERT OR REPLACE INTO verse_roots (surah, ayah, roots) VALUES (?, ?, ?)",
        (surah, ayah, text)
    )

conn.commit()
count = cursor.execute("SELECT COUNT(*) FROM verse_roots").fetchone()[0]
print(f"Loaded {count} verse roots from QUL")

# Show sample
cursor.execute("SELECT * FROM verse_roots WHERE surah = 1 AND ayah = 1")
print(f"Sample 1:1: {cursor.fetchone()}")

conn.close()
qul_conn.close()