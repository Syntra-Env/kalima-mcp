import os
import unittest

# Ensure we never write to disk during tests
os.environ.setdefault('CODEX_READ_ONLY', '1')

from app import app  # noqa: E402


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()

    def test_get_verse(self):
        resp = self.client.get('/api/verse/1/1')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsNotNone(data)
        self.assertEqual(data['surah']['number'], 1)
        self.assertEqual(data['ayah'], 1)

    def test_root_search(self):
        resp = self.client.get('/api/search/roots?root=rHm')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertGreater(data['count'], 0)
        self.assertEqual(data['type'], 'root')

    def test_pronoun_detection(self):
        resp = self.client.get('/api/pronouns/1:5')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertGreater(len(data.get('pronouns', [])), 0)

    def test_pronoun_crud(self):
        # Create
        payload = {
            'pronoun_id': '1:1.1',
            'referent': 'test referent',
            'referent_type': 'entity',
            'status': 'hypothesis',
            'note': 'unit test'
        }
        create = self.client.post('/api/pronouns/1:5', json=payload)
        self.assertEqual(create.status_code, 200)
        ref = create.get_json().get('reference')
        self.assertIsNotNone(ref)
        ref_id = ref['id']

        # Update status
        update = self.client.put(f'/api/pronouns/1:5/{ref_id}', json={'status': 'verified'})
        self.assertEqual(update.status_code, 200)

        # Delete
        delete = self.client.delete(f'/api/pronouns/1:5/{ref_id}')
        self.assertEqual(delete.status_code, 200)

    def test_library_search(self):
        resp = self.client.get('/api/library_search?q=Quran')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertGreaterEqual(data['count'], 1)
        self.assertTrue(any('Quran' in (hit.get('snippet') or '') for hit in data.get('results', [])))


if __name__ == '__main__':
    unittest.main()
