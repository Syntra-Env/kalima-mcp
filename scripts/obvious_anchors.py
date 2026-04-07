
import sqlite3
import re
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "kalima.db"

def anchor_obvious():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Broad Lexical Bridge (Transliteration -> Root/Lemma)
    lexical_bridge = {
        "Jibril": "جبرل",
        "Rasm": "رسم",
        "Harakat": "حرك",
        "Khidr": "خضر",
        "Ard": "أرض",
        "Huda": "هدي",
        "Massa": "مسس",
        "Harun": "هرن",
        "Haman": "همن",
        "Fir'awn": "فرعن",
        "Firawn": "فرعن",
        "Akala": "أكل",
        "Ayyub": "أيب",
        "Musa": "موسى",
        "Muhammad": "حمد",
        "Nafs": "نفس",
        "Malaikah": "ملك",
        "Shaytan": "شطن",
        "Shaitan": "شطن",
        "Quran": "قرأ",
        "Mulk": "ملك",
        "Awwab": "أوب",
        "Zaqqum": "زقم",
        "Harut": "هرت",
        "Marut": "مرت",
        "Qariya": "قري",
        "Masjid": "سجد",
        "Sirat": "صرط",
        "Mustaqim": "قوم",
        "Falaq": "فلق",
        "Bashar": "بشر",
        "Rajul": "رجل",
        "Mar'": "مرا",
        "Imra'at": "مرا",
    }

    # 2. Verse Reference Regex: (2:259) or 38:41
    verse_regex = re.compile(r'\(?(\d+):(\d+)\)?')

    # Get unanchored entries
    entries = cursor.execute("""
        SELECT e.id, e.content 
        FROM entries e
        LEFT JOIN entry_locations el ON e.id = el.entry_id
        WHERE e.feature_id IS NULL AND el.id IS NULL
    """).fetchall()

    print(f"Analyzing {len(entries)} entries for obvious anchors...")

    root_anchors = 0
    verse_anchors = 0

    for entry in entries:
        content = entry['content']
        content_clean = content.replace('ā', 'a').replace('ī', 'i').replace('ū', 'u').replace('ʿ', '').replace('ʾ', '')
        
        anchored = False

        # Pass 1: Verse References (Highest Specificity)
        verse_match = verse_regex.search(content)
        if verse_match:
            sura, aya = int(verse_match.group(1)), int(verse_match.group(2))
            # Basic validation
            if 1 <= sura <= 114:
                cursor.execute(
                    "INSERT OR IGNORE INTO entry_locations (entry_id, surah, ayah_start) VALUES (?, ?, ?)",
                    (entry['id'], sura, aya)
                )
                verse_anchors += 1
                anchored = True

        # Pass 2: Lexical Bridge (Root Matching)
        if not anchored:
            for term, root_ar in lexical_bridge.items():
                # Match term with word boundaries
                if re.search(rf'\b{term}\b', content_clean, re.IGNORECASE):
                    feature = cursor.execute(
                        "SELECT id FROM features WHERE lookup_key = ? AND feature_type = 'root'",
                        (root_ar,)
                    ).fetchone()
                    
                    if feature:
                        cursor.execute("UPDATE entries SET feature_id = ? WHERE id = ?", (feature['id'], entry['id']))
                        root_anchors += 1
                        anchored = True
                        break

    conn.commit()
    print(f"Obvious Anchoring COMPLETE:")
    print(f" - Linked to Roots: {root_anchors}")
    print(f" - Linked to Verses: {verse_anchors}")
    
    remaining = cursor.execute("""
        SELECT COUNT(*) FROM entries e
        LEFT JOIN entry_locations el ON e.id = el.entry_id
        WHERE e.feature_id IS NULL AND el.id IS NULL
    """).fetchone()[0]
    
    print(f"Remaining Unanchored: {remaining}")
    conn.close()

if __name__ == "__main__":
    anchor_obvious()
