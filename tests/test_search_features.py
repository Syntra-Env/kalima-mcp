import os
import unittest
import re

# Keep backend read-only during tests
os.environ.setdefault('CODEX_READ_ONLY', '1')

from app import app  # noqa: E402


def build_segments(word: str):
    """Mirror the front-end splitter: letter buckets with trailing diacritics."""
    segments = []
    is_diacritic = re.compile(r'[\u064B-\u0652\u0670\u0653-\u0655]').match
    is_letter = re.compile(r'[\u0620-\u064a\u0671-\u0673\u0675]').match
    for ch in word:
        if is_diacritic(ch):
            if segments:
                segments[-1]['diacritics'].append(ch)
        elif is_letter(ch):
            segments.append({
                'letter': ch,
                'diacritics': [],
                'any_letter': False,
                'any_diacritics': False
            })
        # ignore tatweel/other marks
    return segments


class SearchFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_pattern_word_search_matches_al_rahman(self):
        word = "ٱلرَّحْمَـٰنِ"
        payload = {
            'segments': build_segments(word),
            'allow_prefix': True,
            'allow_suffix': True
        }
        resp = self.client.post('/api/search/pattern_word', json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertGreater(data.get('count', 0), 0, "Expected pattern search to return matches")

    def test_morphology_search_root_rhm(self):
        resp = self.client.get('/api/search/morphology?q=rhm')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertGreater(data.get('count', 0), 0, "Expected morphology search for root 'rhm' to find matches")

    def test_syntax_search_p_pn_sequence(self):
        # Verse 1:1 contains a preposition (P) followed by a proper noun (PN)
        resp = self.client.get('/api/search/syntax?q=p%20pn')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertGreater(data.get('count', 0), 0, "Expected syntax search for 'p pn' to find matches")

    def test_text_search_bismillah(self):
        resp = self.client.get('/api/search?q=ٱللَّهِ&type=text&limit=5')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertGreater(data.get('count', 0), 0, "Expected text search to return at least one verse")


if __name__ == '__main__':
    unittest.main()
