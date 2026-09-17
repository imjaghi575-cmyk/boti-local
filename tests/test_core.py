import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bot import core


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.memory_path = Path(self.tmp.name) / "memory.json"
        self.patch = patch.object(core, "MEMORY_FILE", self.memory_path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_normalize_persian_variants(self):
        self.assertEqual(core.normalize(" كي  من‌وم ۱۲۳ "), "کی من وم 123")

    def test_reply_greeting(self):
        bot = core.LocalBot()
        self.assertIn("سلام", bot.reply("سلام"))

    def test_input_is_bounded(self):
        bot = core.LocalBot()
        bot.reply("x" * (core.MAX_INPUT_LENGTH + 500))
        self.assertLessEqual(len(bot.memory[-1]["user"]), core.MAX_INPUT_LENGTH)

    def test_name_is_persistent_and_replaceable(self):
        bot = core.LocalBot()
        bot.reply("اسم من علی است")
        bot.reply("اسم من رضا است")
        restored = core.LocalBot()
        self.assertIn("رضا", restored.reply("اسم من چیه"))
        self.assertNotIn("علی", restored.memory_text())

    def test_malformed_memory_is_ignored(self):
        self.memory_path.write_text("{bad json", encoding="utf-8")
        bot = core.LocalBot()
        self.assertEqual(bot.memory, [])

    def test_invalid_memory_items_are_filtered(self):
        self.memory_path.write_text(json.dumps([{"x": 1}, {"user": 12}, {"user": "ok", "bot": "fine"}], ensure_ascii=False), encoding="utf-8")
        bot = core.LocalBot()
        self.assertEqual(len(bot.memory), 1)
        self.assertEqual(bot.memory[0]["user"], "ok")

    def test_clear_memory(self):
        bot = core.LocalBot()
        bot.reply("سلام")
        bot.clear_memory()
        self.assertEqual(bot.memory, [])
        self.assertEqual(json.loads(self.memory_path.read_text(encoding="utf-8")), [])

    def test_memory_limit(self):
        bot = core.LocalBot()
        for index in range(core.MAX_MEMORY_ITEMS + 20):
            bot.reply(f"پیام {index}")
        self.assertLessEqual(len(bot.memory), core.MAX_MEMORY_ITEMS)

    def test_safe_calculator(self):
        bot = core.LocalBot()
        self.assertIn("20", bot.reply("حساب کن: ۱۲ + ۸"))
        self.assertIn("قابل محاسبه نیست", bot.reply("حساب کن: __import__('os')"))
        self.assertIn("25", bot.reply("محاسبه کن: ۵ * ۵"))

    def test_calculator_rejects_division_by_zero(self):
        bot = core.LocalBot()
        self.assertIn("قابل محاسبه نیست", bot.reply("حساب کن: 10 / 0"))


if __name__ == "__main__":
    unittest.main()
