import unittest
from pathlib import Path


class SideMenuStructureTests(unittest.TestCase):
    def setUp(self):
        self.text = Path("templates/index_minimal.html").read_text(encoding="utf-8")

    def test_side_menu_div_balance(self):
        # Extract only the side menu block to avoid counting other sections.
        side_block = self.text.split('<aside id="sideMenu"', 1)[1].split("</aside>", 1)[0]
        open_divs = side_block.count("<div")
        close_divs = side_block.count("</div>")
        self.assertEqual(
            open_divs,
            close_divs,
            f"sideMenu div mismatch: {open_divs} opens vs {close_divs} closes; HTML is malformed",
        )

    def test_side_stacks_present(self):
        self.assertIn('id="sideStacks"', self.text, "stacked side panels missing")


if __name__ == "__main__":
    unittest.main()
