import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bot import core


class CoreTests(unittest.TestCase):
    def test_normalize_persian_variants(self):
        self.assertEqual(core.normalize(" كي  من‌وم "), "کی من وم")

    def test_reply_greeting(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(core, "MEMORY_FILE", Path(tmp) / "memory.json"):
                bot = core.LocalBot()
                self.assertIn("سلام", bot.reply("سلام"))

    def test_input_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(core, "MEMORY_FILE", Path(tmp) / "memory.json"):
                bot = core.LocalBot()
                bot.reply("x" * (core.MAX_INPUT_LENGTH + 500))
                self.assertLessEqual(len(bot.memory[-1]["user"]), core.MAX_INPUT_LENGTH)


if __name__ == "__main__":
    unittest.main()
