
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "scholar.db"

def semantic_anchor():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Define our Lexical Bridge (Concept -> Arabic Root)
    # This covers the most common themes in the remaining entries
    lexical_bridge = {
        "understanding": "فقه",
        "abode": "سكن",
        "dwelling": "سكن",
        "rushed": "عجل",
        "haste": "عجل",
        "blind": "عمي",
        "split": "فلق",
        "purify": "خلص",
        "smelt": "خلص",
        "exhaustion": "تعب",
        "hungry": "جوع",
        "thirsty": "ظمأ",
        "perception": "درك",
        "return": "رجع",
        "homecoming": "رجع",
        "authority": "سلط",
        "authoritative": "سلط",
        "structure": "بني",
        "erected": "بني",
        "block": "سدد",
        "shell": "غلف",
        "enclosure": "حصر",
    }

    # Get unanchored entries
    entries = cursor.execute("""
        SELECT e.id, e.content 
        FROM entries e
        LEFT JOIN entry_locations el ON e.id = el.entry_id
        WHERE e.feature_id IS NULL AND el.id IS NULL
    """).fetchall()

    print(f"Analyzing {len(entries)} unanchored entries for semantic matches...")

    matches = 0
    for entry in entries:
        content = entry['content'].lower()
        
        for concept, root_ar in lexical_bridge.items():
            if concept in content:
                # Find the root feature
                feature = cursor.execute(
                    "SELECT id FROM features WHERE lookup_key = ? AND feature_type = 'root'",
                    (root_ar,)
                ).fetchone()
                
                if feature:
                    cursor.execute(
                        "UPDATE entries SET feature_id = ? WHERE id = ?",
                        (feature['id'], entry['id'])
                    )
                    matches += 1
                    # print(f"Semantically Anchored {entry['id']} ('{concept}') -> {root_ar}")
                    break

    conn.commit()
    print(f"Semantic Anchoring COMPLETE: Linked {matches} entries.")
    
    # Final health check
    remaining = cursor.execute("""
        SELECT COUNT(*) FROM entries e
        LEFT JOIN entry_locations el ON e.id = el.entry_id
        WHERE e.feature_id IS NULL AND el.id IS NULL
    """).fetchone()[0]
    
    print(f"Remaining Unanchored: {remaining}")
    conn.close()

if __name__ == "__main__":
    semantic_anchor()
