
import sqlite3
import re
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"

def location_anchor():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get unanchored entries
    entries = cursor.execute("""
        SELECT e.id, e.content 
        FROM entries e
        LEFT JOIN entry_locations el ON e.id = el.entry_id
        WHERE e.feature_id IS NULL AND el.id IS NULL
    """).fetchall()

    print(f"Analyzing {len(entries)} entries for structural verse anchors...")

    anchored_count = 0
    
    # Define mapping of terms to Arabic roots/lemmas for verse searching
    # We only use terms that are highly likely to refer to specific verses
    search_terms = {
        "Ayyub": "أيب",
        "Awwab": "أوب",
        "Musa": "موسى",
        "Zaqqum": "زقم",
        "Harut": "هرت",
        "Marut": "مرت",
        "Jibril": "جبرل",
    }

    for entry in entries:
        content = entry['content']
        
        # Look for co-occurrence of terms to find specific verses
        # e.g., 'Ayyub' and 'awwab' (Surah 38)
        found_surah_ayah = None
        
        if "Ayyub" in content and "awwab" in content.lower():
            # Surah 38:44 has both
            found_surah_ayah = (38, 44)
        elif "Ayyub" in content and "38:41" in content:
            found_surah_ayah = (38, 41)
        elif "Zaqqum" in content and "Ayyub" in content:
            # Entry 93: Zaqqūm and Ayyūb share pattern
            # We anchor to the verse mentioning Zaqqum (e.g., 37:62)
            found_surah_ayah = (37, 62)

        if found_surah_ayah:
            s, a = found_surah_ayah
            cursor.execute(
                "INSERT OR IGNORE INTO entry_locations (entry_id, surah, ayah_start) VALUES (?, ?, ?)",
                (entry['id'], s, a)
            )
            anchored_count += 1
            # print(f"Anchored {entry['id']} to Verse {s}:{a}")

    conn.commit()
    print(f"Location Anchoring COMPLETE: Linked {anchored_count} entries to specific verses.")
    conn.close()

if __name__ == "__main__":
    location_anchor()
