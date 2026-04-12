import sqlite3
from pathlib import Path

DATA_DIR = Path("data")
db = DATA_DIR / "kalima.db"
qul = DATA_DIR / "ayah-root.db" / "ayah-root.db"

conn = sqlite3.connect(str(db))
qul_conn = sqlite3.connect(str(qul))
cursor = conn.cursor()

# Reset
cursor.execute("UPDATE morpheme_types SET root_id = NULL")

# Get roots 
cursor.execute("SELECT id, lookup_key FROM features WHERE feature_type = 'root'")
root_lookup = {k: v for v, k in cursor.fetchall()}
print(f"Roots in db: {len(root_lookup)}")

# QUL roots by verse - but we need word-level mapping
# This approach can't work cleanly without word-level mapping

# Alternative: Add ALL unique root-text mappings from quran-morphology (ignoring position)
# Get uthmani_text from morpheme_types that already have correct roots from other source
# But we don't have word-level mapping!

# Let's just use QUL data by importing the full QUL database
# And mapping based on text matching where UNIQUE

print("Building text-to-root from QUL verse data...")
# This is hard - QUL has roots at verse level, not word level

# Actually let's just check what we have that works
cursor.execute("SELECT COUNT(*) FROM morpheme_types WHERE root_id IS NOT NULL")
print(f"Current roots: {cursor.fetchone()[0]}")

conn.close()
qul_conn.close()