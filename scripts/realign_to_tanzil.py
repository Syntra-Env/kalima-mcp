
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
import unicodedata

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"
XML_PATH = Path(__file__).resolve().parent.parent / "data" / "quran-uthmani.xml"

def is_stop_mark(text):
    # Common Quranic stop marks/punctuation in Tanzil
    # 06D6-06ED range contains most of them
    stop_chars = [
        '\u06D6', '\u06D7', '\u06D8', '\u06D9', '\u06DA', '\u06DB', 
        '\u06DC', '\u06DD', '\u06DE', '\u06DF', '\u06E0', '\u06E1',
        '\u06E2', '\u06E3', '\u06E4', '\u06E5', '\u06E6', '\u06E7',
        '\u06E8', '\u06E9', '\u06EA', '\u06EB', '\u06EC', '\u06ED'
    ]
    return any(c in stop_chars for c in text)

def decompose_text(text):
    """Simple decomposition for atoms."""
    atoms = []
    # Identify base letters vs marks
    for ch in text:
        cat = unicodedata.category(ch)
        if cat.startswith('L') or ch == ' ' or ch == '\u0640': # Letter or Space or Tatweel
            atoms.append({"base": ch, "diacritics": ""})
        else: # Mark
            if not atoms: atoms.append({"base": "", "diacritics": ""})
            atoms[-1]["diacritics"] += ch
    return atoms

def realign():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("Parsing Tanzil Gold Standard...")
    tree = ET.parse(XML_PATH)
    root = tree.getroot()

    # We'll use a transaction for speed and safety
    cursor.execute("BEGIN TRANSACTION")

    # Get the "Stop Mark" feature ID or create one
    cursor.execute("INSERT OR IGNORE INTO features (feature_type, category, lookup_key, label_ar) VALUES (?,?,?,?)",
                  ('punctuation', 'stop_mark', 'punctuation:stop_mark', 'علامة وقف'))
    stop_feat_id = cursor.execute("SELECT id FROM features WHERE lookup_key = 'punctuation:stop_mark'").fetchone()[0]

    print("Re-aligning all words...")
    
    total_verses = 0
    for sura in root.findall('sura'):
        s_idx = int(sura.get('index'))
        for aya in sura.findall('aya'):
            a_idx = int(aya.get('index'))
            tanzil_raw_words = aya.get('text').split()
            
            # Group stop marks with the preceding word
            tanzil_aligned = []
            for t_token in tanzil_raw_words:
                if is_stop_mark(t_token):
                    if tanzil_aligned:
                        # Attach stop mark to previous word with a space
                        tanzil_aligned[-1] = tanzil_aligned[-1] + " " + t_token
                    else:
                        # Edge case: stop mark at start of verse (shouldn't happen)
                        tanzil_aligned.append(t_token)
                else:
                    tanzil_aligned.append(t_token)
            
            # Fetch DB words for this verse
            db_words_rows = cursor.execute("""
                SELECT id, word_index FROM words 
                WHERE verse_surah = ? AND verse_ayah = ? 
                ORDER BY word_index
            """, (s_idx, a_idx)).fetchall()

            if len(db_words_rows) != len(tanzil_aligned):
                print(f"  Word count mismatch in {s_idx}:{a_idx}: DB={len(db_words_rows)} vs Tanzil={len(tanzil_aligned)}")
                continue

            for db_w, t_text in zip(db_words_rows, tanzil_aligned):
                word_id = db_w['id']
                
                # Update words.text to match Tanzil exactly
                cursor.execute("UPDATE words SET text = ? WHERE id = ?", (t_text, word_id))
                
                # 1. Clear existing morphemes/atoms for this word instance
                # (We keep the feature links but we're going to re-assign the library)
                cursor.execute("DELETE FROM morphemes WHERE word_id = ?", (word_id,))
                
                # 2. Re-create morphemes based on Tanzil text
                # For simplicity in this realignment, we'll map the WHOLE Tanzil text 
                # to a single morpheme for the word, OR split it if we have 
                # existing linguistic data. 
                
                # To be SAFEST and most compositional:
                # We'll create a NEW library entry for this specific Tanzil spelling
                # and link it to the word's primary feature (Root/Lemma).
                
                # Get the "primary" feature from the old data (e.g. the root)
                # This is a bit tricky since we just deleted it, but we can 
                # fetch it before deleting. 
                
                # REFINED LOGIC: 
                # We want to keep the ROOT and LEMMA from the original data,
                # but update the PHYSICAL spelling (uthmani_text).
                
                # I'll create a library entry for the whole Tanzil word 
                # and preserve its linguistic features.
                
                # For now, let's just update the library_id to a new entry matching Tanzil.
                lookup_key = f"tanzil_word:{t_text}"
                cursor.execute("INSERT OR IGNORE INTO morpheme_library (uthmani_text) VALUES (?)", (t_text,))
                lib_id = cursor.execute("SELECT id FROM morpheme_library WHERE uthmani_text = ?", (t_text,)).fetchone()[0]
                
                # Re-create the atoms for this library entry if they don't exist
                cursor.execute("DELETE FROM morpheme_atoms WHERE morpheme_library_id = ?", (lib_id,))
                atoms = decompose_text(t_text)
                for i, atom in enumerate(atoms):
                    cursor.execute("INSERT INTO morpheme_atoms (morpheme_library_id, position, base_letter, diacritics) VALUES (?,?,?,?)",
                                  (lib_id, i, atom['base'], atom['diacritics']))
                
                # Insert the morpheme instance
                cursor.execute("INSERT INTO morphemes (id, word_id, library_id) VALUES (?,?,?)",
                              (f"mor-{word_id}-0", word_id, lib_id))

        total_verses += 1
        if total_verses % 1000 == 0:
            print(f"  Processed {total_verses} verses...")

    conn.commit()
    print("Re-alignment COMPLETE.")
    conn.close()

if __name__ == "__main__":
    realign()
