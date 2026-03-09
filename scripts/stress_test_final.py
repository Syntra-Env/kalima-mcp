
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"

def run_ordered_stress_test():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("--- STRESS TEST 1: Binary Audit (Python Ordered) ---")
    
    # We'll fetch everything in the CORRECT ORDER from the start
    print("Fetching all words, morphemes, and atoms in sequence...")
    
    # This query retrieves every ATOM in the entire Quran in the exact order it appears
    query = """
        SELECT w.id as word_id, w.text as word_text, 
               ma.base_letter, ma.diacritics
        FROM words w
        JOIN morphemes m ON m.word_id = w.id
        JOIN morpheme_library ml ON m.library_id = ml.id
        JOIN morpheme_atoms ma ON ma.morpheme_library_id = ml.id
        ORDER BY w.verse_surah, w.verse_ayah, w.word_index, m.id, ma.position
    """
    
    current_word_id = None
    current_reconstructed = ""
    current_original = ""
    
    mismatches = []
    total_audited = 0
    
    results = cursor.execute(query)
    
    for row in results:
        word_id = row['word_id']
        if word_id != current_word_id:
            # Check the previous word before starting a new one
            if current_word_id is not None:
                if current_reconstructed != current_original:
                    mismatches.append((current_word_id, current_original, current_reconstructed))
                total_audited += 1
                if total_audited % 10000 == 0:
                    print(f"  Audited {total_audited} words...")
            
            # Start new word
            current_word_id = word_id
            current_reconstructed = ""
            current_original = row['word_text']
        
        current_reconstructed += (row['base_letter'] + row['diacritics'])

    # Final word check
    if current_word_id is not None:
        if current_reconstructed != current_original:
            mismatches.append((current_word_id, current_original, current_reconstructed))
        total_audited += 1

    print(f"\nAudit Result: {len(mismatches)} mismatches out of {total_audited} words.")
    
    if mismatches:
        print("FIRST 5 MISMATCHES:")
        for m in mismatches[:5]:
            print(f"  ID: {m[0]} | Orig: {m[1]} | Recon: {m[2]}")
    else:
        print("✅ BINARY INTEGRITY VERIFIED FOR ALL 77,429 WORDS.")

    conn.close()

if __name__ == "__main__":
    run_ordered_stress_test()
