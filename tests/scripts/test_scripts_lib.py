import tempfile
import unittest
from pathlib import Path

from scripts.lib.io import iter_jsonl, write_json, write_jsonl
from scripts.lib.validate import require_file


class ScriptsLibTests(unittest.TestCase):
    def test_write_jsonl_and_iter_jsonl_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "x.jsonl"
            write_jsonl(path, [{"a": 1}, {"b": "two"}])
            self.assertEqual(list(iter_jsonl(path)), [{"a": 1}, {"b": "two"}])

    def test_write_json(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "x.json"
            write_json(path, {"ok": True})
            self.assertTrue(path.read_text(encoding="utf-8").strip().startswith("{"))

    def test_require_file(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "x.txt"
            path.write_text("hi", encoding="utf-8")
            self.assertEqual(require_file(path), path)


if __name__ == "__main__":
    unittest.main()

