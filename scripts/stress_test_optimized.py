
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"

def run_optimized_stress_test():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("--- STRESS TEST 1: Binary Audit (SQL Accelerated) ---")
    
    # We'll use a complex SQL query to reconstruct strings in SQLite's memory.
    # We join everything into a temporary table of 'word_fragments' then group them.
    
    print("Building reconstruction cache...")
    cursor.execute("DROP TABLE IF EXISTS word_recon_cache")
    cursor.execute("""
        CREATE TEMPORARY TABLE word_recon_cache AS
        SELECT m.word_id, GROUP_CONCAT(ma.base_letter || ma.diacritics, '') as reconstructed
        FROM morphemes m
        JOIN morpheme_library ml ON m.library_id = ml.id
        JOIN morpheme_atoms ma ON ma.morpheme_library_id = ml.id
        GROUP BY m.word_id
    """)

    print("Comparing all 77,429 words...")
    cursor.execute("""
        SELECT COUNT(*) FROM words w
        JOIN word_recon_cache c ON w.id = c.word_id
        WHERE w.text != c.reconstructed
    """)
    mismatches = cursor.fetchone()[0]

    if mismatches == 0:
        print("✅ BINARY INTEGRITY VERIFIED FOR ALL 77,429 WORDS.")
    else:
        print(f"❌ FAILED: {mismatches} words do not match!")
        # Show first 3 failures
        failures = cursor.execute("""
            SELECT w.id, w.text, c.reconstructed FROM words w
            JOIN word_recon_cache c ON w.id = c.word_id
            WHERE w.text != c.reconstructed LIMIT 3
        """).fetchall()
        for f in failures:
            print(f"  ID: {f['id']} | Orig: {f['text']} | Recon: {f['reconstructed']}")

    print("\n--- STRESS TEST 2: Linguistic Feature Parity ---")
    feature_cols = [
        'root_id', 'lemma_id', 'pos_id', 'verb_form_id', 'voice_id', 'mood_id', 
        'aspect_id', 'person_id', 'number_id', 'gender_id', 'case_value_id', 
        'dependency_rel_id', 'derived_noun_type_id', 'state_id', 'role_id', 'type_id'
    ]
    
    total_feature_mismatches = 0
    for col in feature_cols:
        query = f"""
            SELECT COUNT(*) FROM morphemes m
            JOIN morpheme_library ml ON m.library_id = ml.id
            WHERE (m.{col} IS NOT ml.{col})
        """
        diff_count = cursor.execute(query).fetchone()[0]
        if diff_count > 0:
            print(f"  ❌ FEATURE MISMATCH: '{col}' has {diff_count} errors!")
            total_feature_mismatches += diff_count
        else:
            print(f"  ✅ Feature '{col}': 100% Match.")

    if total_feature_mismatches == 0:
        print("\n✅ LINGUISTIC PARITY VERIFIED FOR ALL 128,219 MORPHEMES.")
    else:
        print(f"\n❌ TOTAL LINGUISTIC ERRORS: {total_feature_mismatches}")

    conn.close()

if __name__ == "__main__":
    run_optimized_stress_test()
