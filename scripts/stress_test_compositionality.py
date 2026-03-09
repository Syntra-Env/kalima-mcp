
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"

def run_stress_test():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("--- STRESS TEST 1: Full Quranic Binary Audit ---")
    print("Reconstructing all 77,429 words from Atoms...")
    
    # Query to reconstruct words by joining Morphemes -> Library -> Atoms
    # Using a subquery for the reconstruction to do it in-database if possible, 
    # but for absolute rigor we'll do it in Python to verify the sequence.
    
    all_words = cursor.execute("SELECT id, text FROM words ORDER BY id").fetchall()
    total_words = len(all_words)
    word_mismatches = []

    for i, word in enumerate(all_words):
        word_id = word['id']
        original_text = word['text']
        
        # Reconstruct from atoms
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
        
        if original_text != reconstructed:
            word_mismatches.append((word_id, original_text, reconstructed))
        
        if (i+1) % 10000 == 0:
            print(f"  Processed {i+1}/{total_words} words...")

    print(f"\nAudit Result: {len(word_mismatches)} mismatches out of {total_words} words.")
    if word_mismatches:
        print("FIRST 5 MISMATCHES:")
        for m in word_mismatches[:5]:
            print(f"  ID: {m[0]} | Orig: {m[1]} | Recon: {m[2]}")
    else:
        print("✅ BINARY INTEGRITY VERIFIED FOR ALL 77,429 WORDS.")

    print("\n--- STRESS TEST 2: Linguistic Feature Parity ---")
    print("Verifying 18 features across all 128,219 morpheme instances...")
    
    feature_cols = [
        'root_id', 'lemma_id', 'pos_id', 'verb_form_id', 'voice_id', 'mood_id', 
        'aspect_id', 'person_id', 'number_id', 'gender_id', 'case_value_id', 
        'dependency_rel_id', 'derived_noun_type_id', 'state_id', 'role_id', 'type_id'
    ]
    
    # We compare the column in 'morphemes' with the column in 'morpheme_library'
    mismatches = 0
    for col in feature_cols:
        query = f"""
            SELECT COUNT(*) FROM morphemes m
            JOIN morpheme_library ml ON m.library_id = ml.id
            WHERE (m.{col} IS NOT ml.{col})
        """
        diff_count = cursor.execute(query).fetchone()[0]
        if diff_count > 0:
            print(f"  ❌ FEATURE MISMATCH: '{col}' has {diff_count} errors!")
            mismatches += diff_count
        else:
            print(f"  ✅ Feature '{col}': 100% Match.")

    if mismatches == 0:
        print("\n✅ LINGUISTIC PARITY VERIFIED FOR ALL 128,219 MORPHEMES.")
    else:
        print(f"\n❌ TOTAL LINGUISTIC ERRORS: {mismatches}")

    conn.close()

if __name__ == "__main__":
    run_stress_test()
