
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
import unicodedata

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "scholar.db"
XML_PATH = Path(__file__).resolve().parent.parent / "data" / "quran-uthmani.xml"

def run_ordered_audit():
    if not XML_PATH.exists():
        print(f"Error: XML file not found at {XML_PATH}")
        return

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Load Gold Standard into memory for fast lookup
    print("Loading Tanzil Gold Standard...")
    tree = ET.parse(XML_PATH)
    root = tree.getroot()
    gold_standard = {}
    for sura in root.findall('sura'):
        s_idx = int(sura.get('index'))
        for aya in sura.findall('aya'):
            a_idx = int(aya.get('index'))
            gold_standard[(s_idx, a_idx)] = aya.get('text').strip()

    print("--- ORDERED TRUTH AUDIT: Database vs Medina Mushaf ---")
    
    # 2. Single Stream Reconstruction (The "Big Query")
    # We order by verse, then word, then morpheme, then atom position.
    print("Fetching all atoms in global sequence...")
    query = """
        SELECT w.verse_surah, w.verse_ayah, w.word_index, 
               ma.base_letter, ma.diacritics
        FROM words w
        JOIN morphemes m ON m.word_id = w.id
        JOIN morpheme_library ml ON m.library_id = ml.id
        JOIN morpheme_atoms ma ON ma.morpheme_library_id = ml.id
        ORDER BY w.verse_surah, w.verse_ayah, w.word_index, m.id, ma.position
    """
    
    current_verse = (1, 1)
    current_word_index = None
    verse_words = []
    current_word_chars = []
    
    mismatches = 0
    total_verses = 0
    
    results = cursor.execute(query)
    
    for row in results:
        verse = (row['verse_surah'], row['verse_ayah'])
        
        # New Verse Detection
        if verse != current_verse:
            # Finalize previous verse
            if current_word_chars:
                verse_words.append("".join(current_word_chars))
            
            # Since atoms now include spaces, we join with empty string
            db_text = "".join(verse_words)
            gold_text = gold_standard.get(current_verse, "")
            
            if db_text != gold_text:
                mismatches += 1
                if mismatches <= 5:
                    print(f"\nDiscrepancy in Verse {current_verse[0]}:{current_verse[1]}")
                    print(f"  GOLD: {gold_text}")
                    print(f"  DB:   {db_text}")
            
            total_verses += 1
            if total_verses % 1000 == 0:
                print(f"  Audited {total_verses} verses...")
            
            # Reset for new verse
            current_verse = verse
            verse_words = []
            current_word_index = row['word_index']
            current_word_chars = []
        
        # New Word Detection
        if row['word_index'] != current_word_index:
            if current_word_chars:
                verse_words.append("".join(current_word_chars))
            current_word_chars = []
            current_word_index = row['word_index']
            
        current_word_chars.append(row['base_letter'] + row['diacritics'])

    # Final Verse Check
    if current_word_chars:
        verse_words.append("".join(current_word_chars))
    db_text = "".join(verse_words)
    gold_text = gold_standard.get(current_verse, "")
    if db_text != gold_text:
        mismatches += 1

    print(f"\nFinal Audit Result: {mismatches} mismatched verses out of {len(gold_standard)} total.")
    
    if mismatches == 0:
        print("✅ SUCCESS: Database matches Medina Mushaf perfectly.")
    else:
        print("❌ FAILED: Database still contains character-level discrepancies.")

    conn.close()

if __name__ == "__main__":
    run_ordered_audit()
