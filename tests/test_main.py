import unittest
from unittest.mock import patch

import main


class MainTests(unittest.TestCase):
    def test_paint_without_terminal_colors(self):
        with patch.object(main, "USE_COLOR", False):
            self.assertEqual(main.paint(main.GREEN, "سلام"), "سلام")

    def test_paint_with_terminal_colors(self):
        with patch.object(main, "USE_COLOR", True):
            self.assertEqual(main.paint(main.GREEN, "سلام"), "\033[92mسلام\033[0m")


if __name__ == "__main__":
    unittest.main()
