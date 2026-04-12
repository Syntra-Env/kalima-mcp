import sqlite3
from pathlib import Path

DATA_DIR = Path('data')
kalima = sqlite3.connect(str(DATA_DIR / 'kalima.db'))
qul = sqlite3.connect(str(DATA_DIR / 'ayah-root.db' / 'ayah-root.db'))

q_text = qul.execute("SELECT text FROM roots WHERE verse_key = '1:1'").fetchone()[0]
q_set = set(q_text.split())
print('QUL count:', len(q_set))

k_roots = set()
for root, in kalima.execute('''
    SELECT f.lookup_key
    FROM word_instances wi
    JOIN morpheme_types mt ON wi.word_type_id = mt.id
    JOIN features f ON mt.root_id = f.id
    WHERE f.feature_type = "root" AND wi.verse_surah = 1 AND wi.verse_ayah = 1
''').fetchall():
    k_roots.add(root)
print('Kalima count:', len(k_roots))
print('Q - K:', list(q_set - k_roots))
print('K - Q:', list(k_roots - q_set))