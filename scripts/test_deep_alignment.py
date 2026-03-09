
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
import unicodedata

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"
XML_PATH = Path(__file__).resolve().parent.parent / "data" / "quran-uthmani.xml"

def normalize_char(c):
    # Normalize alefs for flexible matching if needed, but we want strict Uthmani
    return c

def get_db_atoms_for_verse(cursor, sura, aya):
    # Fetch all atoms for a verse, ordered by word/morpheme/position
    query = """
        SELECT m.id as morpheme_id, m.word_id, ml.id as lib_id, ma.id as atom_id, 
               ma.base_letter, ma.diacritics, ma.position
        FROM words w
        JOIN morphemes m ON m.word_id = w.id
        JOIN morpheme_library ml ON m.library_id = ml.id
        JOIN morpheme_atoms ma ON ma.morpheme_library_id = ml.id
        WHERE w.verse_surah = ? AND w.verse_ayah = ?
        ORDER BY w.word_index, m.id, ma.position
    """
    return cursor.execute(query, (sura, aya)).fetchall()

def align_verse(sura, aya, tanzil_text, db_atoms):
    # The goal: Map Tanzil characters to DB atoms
    # We reconstruct the DB text from atoms to see where we are
    
    tanzil_idx = 0
    db_atom_idx = 0
    
    # We will build a NEW list of atoms for each morpheme
    # Structure: { morpheme_id: [ {base, diacritics}, ... ] }
    new_morpheme_structure = {}
    
    current_morpheme_id = None
    
    # Flatten DB atoms for easier traversal
    flat_db_atoms = []
    for atom in db_atoms:
        flat_db_atoms.append({
            'morpheme_id': atom['morpheme_id'],
            'word_id': atom['word_id'],
            'base': atom['base_letter'],
            'diacritics': atom['diacritics']
        })
        if atom['morpheme_id'] not in new_morpheme_structure:
            new_morpheme_structure[atom['morpheme_id']] = []

    # Iterate through Tanzil text
    while tanzil_idx < len(tanzil_text):
        t_char = tanzil_text[tanzil_idx]
        
        # 1. Handle Whitespace in Tanzil
        if t_char == ' ':
            # If Tanzil has a space, we append a "Space Atom" to the PREVIOUS morpheme
            # (or the current one if we haven't started)
            target_morpheme = current_morpheme_id or flat_db_atoms[0]['morpheme_id']
            
            # Check if we already have a space there? 
            # Our DB doesn't store spaces in atoms usually.
            new_morpheme_structure[target_morpheme].append({'base': ' ', 'diacritics': ''})
            tanzil_idx += 1
            continue

        # 2. Match against DB Atom
        if db_atom_idx < len(flat_db_atoms):
            db_atom = flat_db_atoms[db_atom_idx]
            current_morpheme_id = db_atom['morpheme_id']
            
            # Is this Tanzil char a Base Letter or a Diacritic?
            is_base = unicodedata.category(t_char).startswith('L') or t_char == '\u0640'
            
            if is_base:
                # Match Base Letter
                if t_char == db_atom['base']:
                    # Perfect match
                    new_atom = {'base': t_char, 'diacritics': ''}
                    # Now consume diacritics from Tanzil until next base letter
                    tanzil_idx += 1
                    while tanzil_idx < len(tanzil_text):
                        next_t = tanzil_text[tanzil_idx]
                        if unicodedata.category(next_t).startswith('M') or next_t in ['\u06D6', '\u06DB', '\u06D7']: # Mark or Stop
                            new_atom['diacritics'] += next_t
                            tanzil_idx += 1
                        else:
                            break
                    new_morpheme_structure[current_morpheme_id].append(new_atom)
                    db_atom_idx += 1
                else:
                    # Mismatch!
                    # Case A: Tanzil has a letter DB doesn't (Insertion)
                    # We insert it into current morpheme
                    new_atom = {'base': t_char, 'diacritics': ''}
                    tanzil_idx += 1
                    while tanzil_idx < len(tanzil_text):
                        next_t = tanzil_text[tanzil_idx]
                        if unicodedata.category(next_t).startswith('M') or next_t in ['\u06D6', '\u06DB', '\u06D7']:
                            new_atom['diacritics'] += next_t
                            tanzil_idx += 1
                        else:
                            break
                    new_morpheme_structure[current_morpheme_id].append(new_atom)
                    # We do NOT advance db_atom_idx because we haven't consumed the DB atom yet
            else:
                # Tanzil char is a mark/symbol but we expected a base letter?
                # This usually means it's a stop mark or symbol attached to previous atom
                # Attach to previous atom in new structure
                if new_morpheme_structure[current_morpheme_id]:
                    new_morpheme_structure[current_morpheme_id][-1]['diacritics'] += t_char
                else:
                    # Very edge case: Mark at start of morpheme? 
                    # Create a placeholder atom
                    new_morpheme_structure[current_morpheme_id].append({'base': '', 'diacritics': t_char})
                tanzil_idx += 1
        else:
            # End of DB atoms, but Tanzil still has text?
            # Append remaining Tanzil text to last morpheme
            last_morph = list(new_morpheme_structure.keys())[-1]
             # Is this Tanzil char a Base Letter?
            is_base = unicodedata.category(t_char).startswith('L') or t_char == '\u0640'
            if is_base:
                new_atom = {'base': t_char, 'diacritics': ''}
                tanzil_idx += 1
                while tanzil_idx < len(tanzil_text):
                    next_t = tanzil_text[tanzil_idx]
                    if unicodedata.category(next_t).startswith('M'):
                        new_atom['diacritics'] += next_t
                        tanzil_idx += 1
                    else:
                        break
                new_morpheme_structure[last_morph].append(new_atom)
            else:
                 if new_morpheme_structure[last_morph]:
                    new_morpheme_structure[last_morph][-1]['diacritics'] += t_char
                 tanzil_idx += 1

    return new_morpheme_structure

def run_test_alignment():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    tree = ET.parse(XML_PATH)
    root = tree.getroot()
    
    # Test Verse 2:2
    sura, aya = 2, 2
    tanzil_text = root.findall(f".//sura[@index='{sura}']/aya[@index='{aya}']")[0].get('text')
    print(f"Target Tanzil Text: {tanzil_text}")
    
    db_atoms = get_db_atoms_for_verse(cursor, sura, aya)
    print(f"DB Atom Count: {len(db_atoms)}")
    
    new_structure = align_verse(sura, aya, tanzil_text, db_atoms)
    
    # Verify Reconstruction
    recon_str = ""
    for m_id, atoms in new_structure.items():
        for a in atoms:
            recon_str += a['base'] + a['diacritics']
    
    print(f"Reconstructed:    {recon_str}")
    
    if tanzil_text == recon_str:
        print("✅ ALIGNMENT SUCCESSFUL")
    else:
        print("❌ ALIGNMENT FAILED")
        # Compare
        for i in range(min(len(tanzil_text), len(recon_str))):
            if tanzil_text[i] != recon_str[i]:
                print(f"Diff at {i}: '{tanzil_text[i]}' vs '{recon_str[i]}'")
                break

    conn.close()

if __name__ == "__main__":
    run_test_alignment()
