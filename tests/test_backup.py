import json
import tempfile
import unittest
from pathlib import Path

from bot.backup import import_memory, export_memory


class BackupTests(unittest.TestCase):
    def test_round_trip_is_bounded(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "memory-backup.json"
            export_memory([{"user": str(i)} for i in range(200)], target)
            restored = import_memory(target)
            self.assertEqual(len(restored), 150)
            self.assertEqual(restored[0]["user"], "50")

    def test_invalid_top_level_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "bad.json"
            source.write_text(json.dumps({"bad": True}), encoding="utf-8")
            with self.assertRaises(ValueError):
                import_memory(source)


if __name__ == "__main__":
    unittest.main()
