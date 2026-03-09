
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
import unicodedata

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"
XML_PATH = Path(__file__).resolve().parent.parent / "data" / "quran-uthmani.xml"

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

def align_verse(tanzil_text, db_atoms):
    tanzil_idx = 0
    db_atom_idx = 0
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
            target_morpheme = current_morpheme_id or (flat_db_atoms[0]['morpheme_id'] if flat_db_atoms else None)
            if target_morpheme:
                new_morpheme_structure[target_morpheme].append({'base': ' ', 'diacritics': ''})
            tanzil_idx += 1
            continue

        # 2. Match against DB Atom
        if db_atom_idx < len(flat_db_atoms):
            db_atom = flat_db_atoms[db_atom_idx]
            current_morpheme_id = db_atom['morpheme_id']
            
            is_base = unicodedata.category(t_char).startswith('L') or t_char == '\u0640'
            
            if is_base:
                if t_char == db_atom['base']: # Match
                    new_atom = {'base': t_char, 'diacritics': ''}
                    tanzil_idx += 1
                    while tanzil_idx < len(tanzil_text):
                        next_t = tanzil_text[tanzil_idx]
                        if unicodedata.category(next_t).startswith('M') or next_t in ['\u06D6', '\u06DB', '\u06D7', '\u06DE', '\u06DF', '\u06E9', '\u06EA', '\u06EB', '\u06EC', '\u06ED']:
                            new_atom['diacritics'] += next_t
                            tanzil_idx += 1
                        else:
                            break
                    new_morpheme_structure[current_morpheme_id].append(new_atom)
                    db_atom_idx += 1
                else: # Mismatch/Insertion
                    new_atom = {'base': t_char, 'diacritics': ''}
                    tanzil_idx += 1
                    while tanzil_idx < len(tanzil_text):
                        next_t = tanzil_text[tanzil_idx]
                        if unicodedata.category(next_t).startswith('M') or next_t in ['\u06D6', '\u06DB', '\u06D7', '\u06DE', '\u06DF', '\u06E9', '\u06EA', '\u06EB', '\u06EC', '\u06ED']:
                            new_atom['diacritics'] += next_t
                            tanzil_idx += 1
                        else:
                            break
                    new_morpheme_structure[current_morpheme_id].append(new_atom)
                    # Don't advance DB atom
            else: # Orphan Mark
                if new_morpheme_structure[current_morpheme_id]:
                    new_morpheme_structure[current_morpheme_id][-1]['diacritics'] += t_char
                else:
                     new_morpheme_structure[current_morpheme_id].append({'base': '', 'diacritics': t_char})
                tanzil_idx += 1
        else: # Tanzil remainder
            # Append to last morpheme
            last_morph = list(new_morpheme_structure.keys())[-1]
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

def realign_global():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("Parsing Tanzil XML...")
    tree = ET.parse(XML_PATH)
    root = tree.getroot()

    print("--- GLOBAL DEEP ALIGNMENT ---")
    cursor.execute("BEGIN TRANSACTION")

    total_verses = 0
    
    for sura in root.findall('sura'):
        s_idx = int(sura.get('index'))
        for aya in sura.findall('aya'):
            a_idx = int(aya.get('index'))
            tanzil_text = aya.get('text').strip()
            
            db_atoms = get_db_atoms_for_verse(cursor, s_idx, a_idx)
            
            # Perform alignment
            try:
                new_structure = align_verse(tanzil_text, db_atoms)
            except Exception as e:
                print(f"Error aligning {s_idx}:{a_idx}: {e}")
                continue
            
            # Persist changes
            # We iterate through the NEW morpheme structure and update the LIBRARY and ATOMS
            # Note: This changes the DEFINITION of the morpheme in the library.
            # If multiple morphemes shared the same library ID but now have different contexts 
            # (e.g., one has a stop mark, one doesn't), we must FORK the library entry.
            
            # To be safe and simple: We will create NEW library entries for every morpheme in this verse.
            # This de-duplicates later naturally if we run a cleanup script.
            
            for m_id, atoms in new_structure.items():
                # Reconstruct text for this morpheme
                m_text = "".join([a['base'] + a['diacritics'] for a in atoms])
                
                # Create NEW library entry
                cursor.execute("INSERT INTO morpheme_library (uthmani_text) VALUES (?)", (m_text,))
                new_lib_id = cursor.lastrowid
                
                # Link morpheme instance to new library ID
                cursor.execute("UPDATE morphemes SET library_id = ? WHERE id = ?", (new_lib_id, m_id))
                
                # Insert atoms for new library ID
                for i, atom in enumerate(atoms):
                    cursor.execute("""
                        INSERT INTO morpheme_atoms (morpheme_library_id, position, base_letter, diacritics)
                        VALUES (?, ?, ?, ?)
                    """, (new_lib_id, i, atom['base'], atom['diacritics']))

            total_verses += 1
            if total_verses % 1000 == 0:
                print(f"  Aligned {total_verses} verses...")

    # Cleanup: Remove old/orphaned library entries and atoms
    # (Optional but good for hygiene)
    
    conn.commit()
    print("Global Alignment COMPLETE.")
    conn.close()

if __name__ == "__main__":
    realign_global()
