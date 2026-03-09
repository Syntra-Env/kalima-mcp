
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"

def migrate():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Add feature_id to morpheme_library if not exists
    print("Preparing morpheme_library...")
    try:
        cursor.execute("ALTER TABLE morpheme_library ADD COLUMN feature_id INTEGER REFERENCES features(id)")
    except sqlite3.OperationalError:
        pass

    # 2. Get all unique morphemes from the library
    print("Fetching unique morphemes...")
    lib_entries = cursor.execute("SELECT id, uthmani_text FROM morpheme_library").fetchall()

    # 3. Insert into features table
    print(f"Registering {len(lib_entries)} morphemes in the features table...")
    
    # Prepare batch of data
    features_batch = []
    for entry in lib_entries:
        uthmani = entry['uthmani_text']
        lookup_key = f"morpheme:{uthmani}:{entry['id']}"
        features_batch.append(('morpheme', 'morpheme', lookup_key, uthmani, 0))

    # Bulk insert features
    cursor.executemany("""
        INSERT OR IGNORE INTO features (feature_type, category, lookup_key, label_ar, frequency)
        VALUES (?, ?, ?, ?, ?)
    """, features_batch)
    conn.commit()

    # Link back to library in chunks for better performance
    print("Linking library entries to new features...")
    cursor.execute("""
        UPDATE morpheme_library
        SET feature_id = (
            SELECT id FROM features 
            WHERE lookup_key = 'morpheme:' || uthmani_text || ':' || morpheme_library.id
        )
    """)
    conn.commit()

    # 4. Update frequency in features for morphemes
    print("Calculating frequencies (this might take a moment)...")
    # Optimize by grouping morphemes first
    cursor.execute("""
        CREATE TEMPORARY TABLE morpheme_counts AS
        SELECT ml.feature_id, COUNT(*) as cnt
        FROM morphemes m 
        JOIN morpheme_library ml ON m.library_id = ml.id 
        GROUP BY ml.feature_id
    """)
    
    cursor.execute("""
        UPDATE features 
        SET frequency = (SELECT cnt FROM morpheme_counts WHERE feature_id = features.id)
        WHERE feature_type = 'morpheme'
    """)
    conn.commit()

    conn.commit()
    print("Migration successful: Morphemes are now unified in the features registry.")
    
    # Verification
    sample = cursor.execute("""
        SELECT f.id, f.label_ar, f.frequency, ml.id as lib_id 
        FROM features f 
        JOIN morpheme_library ml ON ml.feature_id = f.id 
        LIMIT 3
    """).fetchall()
    for s in sample:
        print(f"Feature {s['id']}: {s['label_ar']} (Freq: {s['frequency']}, LibID: {s['lib_id']})")

    conn.close()

if __name__ == "__main__":
    migrate()
