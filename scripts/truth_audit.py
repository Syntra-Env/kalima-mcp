
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
import unicodedata

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"
XML_PATH = Path(__file__).resolve().parent.parent / "data" / "quran-uthmani.xml"

def normalize_string(s):
    # Standardize normalization for comparison
    return unicodedata.normalize('NFC', s.strip())

def run_truth_audit():
    if not XML_PATH.exists():
        print(f"Error: XML file not found at {XML_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("Parsing Tanzil XML...")
    tree = ET.parse(XML_PATH)
    root = tree.getroot()

    print("--- TRUTH AUDIT: Database vs Medina Mushaf (Tanzil) ---")
    
    total_verses = 0
    mismatched_verses = 0
    
    # Tanzil XML structure: <quran><sura index="1"><aya index="1" text="..."/></sura></quran>
    for sura in root.findall('sura'):
        sura_index = int(sura.get('index'))
        for aya in sura.findall('aya'):
            aya_index = int(aya.get('index'))
            tanzil_text = normalize_string(aya.get('text'))
            total_verses += 1
            
            # Reconstruct verse from our ATOMS
            # Path: Verse -> Words -> Morphemes -> Library -> Atoms
            query = """
                SELECT ma.base_letter, ma.diacritics
                FROM words w
                JOIN morphemes m ON m.word_id = w.id
                JOIN morpheme_library ml ON m.library_id = ml.id
                JOIN morpheme_atoms ma ON ma.morpheme_library_id = ml.id
                WHERE w.verse_surah = ? AND w.verse_ayah = ?
                ORDER BY w.word_index ASC, m.id ASC, ma.position ASC
            """
            atoms = cursor.execute(query, (sura_index, aya_index)).fetchall()
            
            # Words in Tanzil are space-separated
            # Our atoms don't include spaces between words (words table handles those)
            # So we reconstruct words and join them with space.
            
            word_query = "SELECT id FROM words WHERE verse_surah = ? AND verse_ayah = ? ORDER BY word_index"
            word_ids = [r['id'] for r in cursor.execute(word_query, (sura_index, aya_index)).fetchall()]
            
            reconstructed_words = []
            for w_id in word_ids:
                w_atoms = cursor.execute("""
                    SELECT ma.base_letter, ma.diacritics
                    FROM morphemes m
                    JOIN morpheme_library ml ON m.library_id = ml.id
                    JOIN morpheme_atoms ma ON ma.morpheme_library_id = ml.id
                    WHERE m.word_id = ?
                    ORDER BY m.id ASC, ma.position ASC
                """, (w_id,)).fetchall()
                reconstructed_words.append("".join([a['base_letter'] + a['diacritics'] for a in w_atoms]))
            
            db_verse_text = normalize_string(" ".join(reconstructed_words))
            
            if tanzil_text != db_verse_text:
                mismatched_verses += 1
                if mismatched_verses <= 5:
                    print(f"\nMISMATCH in Verse {sura_index}:{aya_index}")
                    print(f"  Tanzil: {tanzil_text}")
                    print(f"  DB:     {db_verse_text}")
                    
                    # Highlight diffs (first 10 chars)
                    for i in range(min(len(tanzil_text), len(db_verse_text))):
                        if tanzil_text[i] != db_verse_text[i]:
                            print(f"  Diff at index {i}: '{tanzil_text[i]}' (U+{ord(tanzil_text[i]):04X}) vs '{db_verse_text[i]}' (U+{ord(db_verse_text[i]):04X})")
                            break
            
            if total_verses % 1000 == 0:
                print(f"  Audited {total_verses} verses...")

    print(f"\nFinal Audit Result: {mismatched_verses} mismatched verses out of {total_verses}.")
    
    if mismatched_verses == 0:
        print("✅ DATABASE IS CHARACTER-PERFECT TO THE MEDINA MUSHAF.")
    else:
        print("❌ DATABASE CONTAINS NOISE/DISCREPANCIES.")

    conn.close()

if __name__ == "__main__":
    run_truth_audit()
