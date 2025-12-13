import sqlite3
import json

conn = sqlite3.connect('data/database/kalima.db')
cursor = conn.cursor()
cursor.execute('SELECT text FROM tokens WHERE verse_surah = 2 AND verse_ayah = 282 ORDER BY token_index')
tokens = [row[0] for row in cursor.fetchall()]

with open('tokens_2_282.json', 'w', encoding='utf-8') as f:
    json.dump(tokens, f, ensure_ascii=False, indent=2)
