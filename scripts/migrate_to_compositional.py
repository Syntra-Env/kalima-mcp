
import sqlite3
import unicodedata
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"

def is_arabic_base_letter(ch: str) -> bool:
    """Check if a character is an Arabic base letter (not a diacritic).
    We include Hamza and variants like Alef with Hamza as base letters,
    since they 'carry' diacritics in orthography.
    """
    cat = unicodedata.category(ch)
    # Lo = Letter, Other (most Arabic letters)
    # 0621-064A: Standard Arabic letters
    # 0640: Tatweel (counts as a base for marks)
    # 06D2, 06D3: Yeh Barree
    code = ord(ch)
    return (cat == 'Lo' or code == 0x0640) and (0x0600 <= code <= 0x06FF)

def decompose_morpheme(text: str) -> list[dict]:
    """Decompose an Uthmani string into atoms (base letter + diacritics)."""
    atoms = []
    current_atom = None

    for ch in text:
        if is_arabic_base_letter(ch):
            # Start a new atom
            if current_atom:
                atoms.append(current_atom)
            current_atom = {"base": ch, "diacritics": ""}
        else:
            # It's a diacritic (Mark)
            if not current_atom:
                # Edge case: starts with a mark (e.g., in a fragment)
                current_atom = {"base": "", "diacritics": ""}
            current_atom["diacritics"] += ch

    if current_atom:
        atoms.append(current_atom)
    return atoms

def migrate():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("Creating new compositional tables...")
    cursor.execute("DROP TABLE IF EXISTS morpheme_atoms")
    cursor.execute("DROP TABLE IF EXISTS morpheme_library")
    
    cursor.execute("""
        CREATE TABLE morpheme_library (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            uthmani_text TEXT NOT NULL,
            root_id INTEGER,
            lemma_id INTEGER,
            pos_id INTEGER,
            verb_form_id INTEGER,
            voice_id INTEGER,
            mood_id INTEGER,
            aspect_id INTEGER,
            person_id INTEGER,
            number_id INTEGER,
            gender_id INTEGER,
            case_value_id INTEGER,
            dependency_rel_id INTEGER,
            derived_noun_type_id INTEGER,
            state_id INTEGER,
            role_id INTEGER,
            type_id INTEGER,
            UNIQUE(uthmani_text, root_id, lemma_id, pos_id, verb_form_id, voice_id, mood_id, aspect_id, 
                   person_id, number_id, gender_id, case_value_id, dependency_rel_id, 
                   derived_noun_type_id, state_id, role_id, type_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE morpheme_atoms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            morpheme_library_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            base_letter TEXT,
            diacritics TEXT,
            FOREIGN KEY (morpheme_library_id) REFERENCES morpheme_library(id)
        )
    """)

    # Add library_id to morphemes if not exists
    try:
        cursor.execute("ALTER TABLE morphemes ADD COLUMN library_id INTEGER REFERENCES morpheme_library(id)")
    except sqlite3.OperationalError:
        pass

    print("Extracting unique morphemes into library...")
    # Fetch all unique combinations
    unique_morphemes = cursor.execute("""
        SELECT DISTINCT 
            uthmani_form, root_id, lemma_id, pos_id, verb_form_id, voice_id, 
            mood_id, aspect_id, person_id, number_id, gender_id, case_value_id, 
            dependency_rel_id, derived_noun_type_id, state_id, role_id, type_id
        FROM morphemes
    """).fetchall()

    for row in unique_morphemes:
        # Insert into library
        keys = row.keys()
        placeholders = ", ".join(["?" for _ in keys])
        columns = ", ".join(keys).replace("uthmani_form", "uthmani_text")
        
        cursor.execute(f"INSERT OR IGNORE INTO morpheme_library ({columns}) VALUES ({placeholders})", list(row))
        # Fetch the ID of the inserted or existing row
        where_clause = " AND ".join([f"{k.replace('uthmani_form', 'uthmani_text')} IS ?" for k in keys])
        lib_id = cursor.execute(f"SELECT id FROM morpheme_library WHERE {where_clause}", list(row)).fetchone()[0]

        # Decompose into atoms
        atoms = decompose_morpheme(row['uthmani_form'])
        for i, atom in enumerate(atoms):
            cursor.execute("""
                INSERT INTO morpheme_atoms (morpheme_library_id, position, base_letter, diacritics)
                VALUES (?, ?, ?, ?)
            """, (lib_id, i, atom['base'], atom['diacritics']))

    print("Mapping morphemes to library...")
    cursor.execute("""
        UPDATE morphemes
        SET library_id = (
            SELECT id FROM morpheme_library ml
            WHERE ml.uthmani_text = morphemes.uthmani_form
              AND (ml.root_id IS morphemes.root_id OR (ml.root_id IS NULL AND morphemes.root_id IS NULL))
              AND (ml.lemma_id IS morphemes.lemma_id OR (ml.lemma_id IS NULL AND morphemes.lemma_id IS NULL))
              AND (ml.pos_id IS morphemes.pos_id OR (ml.pos_id IS NULL AND morphemes.pos_id IS NULL))
              AND (ml.verb_form_id IS morphemes.verb_form_id OR (ml.verb_form_id IS NULL AND morphemes.verb_form_id IS NULL))
              AND (ml.voice_id IS morphemes.voice_id OR (ml.voice_id IS NULL AND morphemes.voice_id IS NULL))
              AND (ml.mood_id IS morphemes.mood_id OR (ml.mood_id IS NULL AND morphemes.mood_id IS NULL))
              AND (ml.aspect_id IS morphemes.aspect_id OR (ml.aspect_id IS NULL AND morphemes.aspect_id IS NULL))
              AND (ml.person_id IS morphemes.person_id OR (ml.person_id IS NULL AND morphemes.person_id IS NULL))
              AND (ml.number_id IS morphemes.number_id OR (ml.number_id IS NULL AND morphemes.number_id IS NULL))
              AND (ml.gender_id IS morphemes.gender_id OR (ml.gender_id IS NULL AND morphemes.gender_id IS NULL))
              AND (ml.case_value_id IS morphemes.case_value_id OR (ml.case_value_id IS NULL AND morphemes.case_value_id IS NULL))
              AND (ml.dependency_rel_id IS morphemes.dependency_rel_id OR (ml.dependency_rel_id IS NULL AND morphemes.dependency_rel_id IS NULL))
              AND (ml.derived_noun_type_id IS morphemes.derived_noun_type_id OR (ml.derived_noun_type_id IS NULL AND morphemes.derived_noun_type_id IS NULL))
              AND (ml.state_id IS morphemes.state_id OR (ml.state_id IS NULL AND morphemes.state_id IS NULL))
              AND (ml.role_id IS morphemes.role_id OR (ml.role_id IS NULL AND morphemes.role_id IS NULL))
              AND (ml.type_id IS morphemes.type_id OR (ml.type_id IS NULL AND morphemes.type_id IS NULL))
        )
    """)

    conn.commit()
    print("Migration complete. Verifying integrity...")

    # Verification: Reconstruct word 2:107:14
    test_word_id = '2:107:14'
    reconstructed_segments = []
    word_morphemes = cursor.execute("""
        SELECT ml.id, m.id as mor_instance_id
        FROM morphemes m
        JOIN morpheme_library ml ON m.library_id = ml.id
        WHERE m.word_id = ?
        ORDER BY m.id
    """, (test_word_id,)).fetchall()
    
    for m in word_morphemes:
        morpheme_text = ""
        # Get atoms for this morpheme instance
        atoms = cursor.execute("""
            SELECT base_letter, diacritics
            FROM morpheme_atoms
            WHERE morpheme_library_id = ?
            ORDER BY position
        """, (m['id'],)).fetchall()
        for a in atoms:
            morpheme_text += (a['base_letter'] + a['diacritics'])
        reconstructed_segments.append(morpheme_text)
    
    reconstructed = "".join(reconstructed_segments)
    original = cursor.execute("SELECT text FROM words WHERE id = ?", (test_word_id,)).fetchone()[0]
    print(f"Word {test_word_id}:")
    print(f"  Original:    {original}")
    print(f"  Reconstructed: {reconstructed}")
    
    if original == reconstructed:
        print("Verification SUCCESS for test word.")
    else:
        print("Verification FAILED for test word.")

    conn.close()

if __name__ == "__main__":
    migrate()
