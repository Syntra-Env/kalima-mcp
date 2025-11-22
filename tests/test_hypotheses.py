import unittest
import os

os.environ.setdefault('CODEX_READ_ONLY', '1')

from app import app, corpus  # noqa: E402


class HypothesisTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_unified_hypothesis_created_with_pronoun(self):
        payload = {
            'pronoun_id': '1:1.1',
            'referent': 'test',
            'status': 'hypothesis'
        }
        resp = self.client.post('/api/pronouns/1:5', json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        ref = data.get('reference')
        self.assertIsNotNone(ref)

        verse = corpus.get_verse(1, 5)
        hyps = [h for h in verse.get('structure_hypotheses', []) if h.get('target_type') == 'pronoun' and h.get('target_id') == '1:1.1']
        self.assertGreaterEqual(len(hyps), 1)


if __name__ == '__main__':
    unittest.main()
