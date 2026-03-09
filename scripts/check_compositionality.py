
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"

def check_compositionality():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Test words: Bismillah (1:1:1), Al-Hamdu (1:2:1), and our favorite test word (2:107:14)
    test_ids = ['1:1:1', '1:2:1', '2:107:14', '114:6:2']
    
    print(f"{'Word ID':<10} | {'Original':<15} | {'Reconstructed':<15} | {'Status'}")
    print("-" * 60)

    for word_id in test_ids:
        # 1. Get original text
        original = cursor.execute("SELECT text FROM words WHERE id = ?", (word_id,)).fetchone()['text']
        
        # 2. Reconstruct from Atoms
        # Path: Word -> Morphemes -> Library -> Atoms
        query = """
            SELECT ma.base_letter, ma.diacritics
            FROM morphemes m
            JOIN morpheme_library ml ON m.library_id = ml.id
            JOIN morpheme_atoms ma ON ma.morpheme_library_id = ml.id
            WHERE m.word_id = ?
            ORDER BY m.id ASC, ma.position ASC
        """
        atoms = cursor.execute(query, (word_id,)).fetchall()
        reconstructed = "".join([(a['base_letter'] + a['diacritics']) for a in atoms])
        
        status = "✅ MATCH" if original == reconstructed else "❌ FAIL"
        print(f"{word_id:<10} | {original:<15} | {reconstructed:<15} | {status}")

    # Global Audit: Count any mismatches in the first 1000 words
    print("\nRunning global sample audit (first 1000 words)...")
    mismatches = 0
    sample_words = cursor.execute("SELECT id, text FROM words LIMIT 1000").fetchall()
    
    for row in sample_words:
        w_id = row['id']
        orig = row['text']
        
        atoms = cursor.execute(query, (w_id,)).fetchall()
        recon = "".join([(a['base_letter'] + a['diacritics']) for a in atoms])
        
        if orig != recon:
            mismatches += 1
            if mismatches < 5:
                print(f"Mismatch in {w_id}: '{orig}' vs '{recon}'")

    if mismatches == 0:
        print("Global Sample Audit: 100% SUCCESS (0 mismatches in 1000 words)")
    else:
        print(f"Global Sample Audit: FAILED with {mismatches} mismatches.")

    conn.close()

if __name__ == "__main__":
    check_compositionality()
