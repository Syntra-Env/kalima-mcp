
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "scholar.db"
XML_PATH = Path(__file__).resolve().parent.parent / "data" / "quran-uthmani.xml"

def run_fast_audit():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 1. Create a table for the Gold Standard
    print("Creating Gold Standard table...")
    cursor.execute("DROP TABLE IF EXISTS gold_standard")
    cursor.execute("CREATE TABLE gold_standard (surah INTEGER, ayah INTEGER, text TEXT)")
    
    # 2. Parse XML and bulk insert
    print("Parsing and loading Tanzil XML...")
    tree = ET.parse(XML_PATH)
    root = tree.getroot()
    gold_data = []
    for sura in root.findall('sura'):
        s_idx = int(sura.get('index'))
        for aya in sura.findall('aya'):
            a_idx = int(aya.get('index'))
            gold_data.append((s_idx, a_idx, aya.get('text').strip()))
    
    cursor.executemany("INSERT INTO gold_standard VALUES (?, ?, ?)", gold_data)
    conn.commit()

    # 3. High-speed reconstruction and comparison
    # We use a CTE (Common Table Expression) to reconstruct words, then verses.
    print("Reconstructing and auditing (this is the fast part)...")
    
    # First, reconstruct morphemes from atoms
    cursor.execute("DROP TABLE IF EXISTS tmp_mor_recon")
    cursor.execute("""
        CREATE TEMPORARY TABLE tmp_mor_recon AS
        SELECT ml.id as lib_id, GROUP_CONCAT(ma.base_letter || ma.diacritics, '') as txt
        FROM morpheme_library ml
        JOIN morpheme_atoms ma ON ma.morpheme_library_id = ml.id
        GROUP BY ml.id
    """)

    # Second, reconstruct words from morphemes
    cursor.execute("DROP TABLE IF EXISTS tmp_word_recon")
    cursor.execute("""
        CREATE TEMPORARY TABLE tmp_word_recon AS
        SELECT m.word_id, GROUP_CONCAT(tmr.txt, '') as txt
        FROM morphemes m
        JOIN tmp_mor_recon tmr ON m.library_id = tmr.lib_id
        GROUP BY m.word_id
    """)

    # Third, reconstruct verses and compare
    cursor.execute("""
        WITH verse_recon AS (
            SELECT w.verse_surah, w.verse_ayah, GROUP_CONCAT(twr.txt, ' ') as db_text
            FROM words w
            JOIN tmp_word_recon twr ON w.id = twr.word_id
            GROUP BY w.verse_surah, w.verse_ayah
        )
        SELECT g.surah, g.ayah, g.text as gold_text, vr.db_text
        FROM gold_standard g
        JOIN verse_recon vr ON g.surah = vr.verse_surah AND g.ayah = vr.verse_ayah
        WHERE g.text != vr.db_text
    """)
    
    mismatches = cursor.fetchall()
    
    print(f"\nAudit Result: {len(mismatches)} mismatched verses.")
    
    if mismatches:
        print("\nFIRST 3 DISCREPANCIES:")
        for m in mismatches[:3]:
            s, a, gold, db = m
            print(f"Verse {s}:{a}")
            print(f"  GOLD: {gold}")
            print(f"  DB:   {db}")
            
            # Find the first differing character
            for i in range(min(len(gold), len(db))):
                if gold[i] != db[i]:
                    print(f"  Error at index {i}: '{gold[i]}' (U+{ord(gold[i]):04X}) vs '{db[i]}' (U+{ord(db[i]):04X})")
                    break
    else:
        print("✅ SUCCESS: The database atoms perfectly match the Medina Mushaf (Tanzil).")

    conn.close()

if __name__ == "__main__":
    run_fast_audit()
