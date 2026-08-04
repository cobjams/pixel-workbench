import unittest
from PIL import Image
from pixel_workbench.app import Workbench
from pixel_workbench.core.document import Document
from pixel_workbench.analysis.sprite_analysis import SpriteAnalysis

class TestDecomposition(unittest.TestCase):
    def setUp(self):
        self.wb = Workbench()

    def test_semantic_regions_head_body(self):
        # Create a mock 16x15 Document
        img = Image.new("RGBA", (16, 15), (0, 0, 0, 0))
        pixels = img.load()

        # Color top half (head) with red
        for y in range(8):
            for x in range(16):
                pixels[x, y] = (255, 0, 0, 255)

        # Color bottom half (body) with blue
        for y in range(8, 15):
            for x in range(16):
                pixels[x, y] = (0, 0, 255, 255)

        doc = Document()
        doc.image = img

        analysis = self.wb.analyze(doc)

        head_region = analysis.get_region("head")
        body_region = analysis.get_region("body")

        self.assertEqual(len(head_region), 16 * 8)
        self.assertEqual(len(body_region), 16 * 7)

        # Verify head is in top half
        for x, y in head_region:
            self.assertTrue(y < 8)

        # Verify body is in bottom half
        for x, y in body_region:
            self.assertTrue(y >= 8)

    def test_semantic_regions_shadow_highlight(self):
        # Create a mock 16x15 Document
        img = Image.new("RGBA", (16, 15), (0, 0, 0, 0))
        pixels = img.load()

        # Three shades of red: dark, mid, bright
        dark_red = (100, 0, 0, 255)
        mid_red = (180, 0, 0, 255)
        bright_red = (255, 0, 0, 255)

        # Draw some pixels with these colors
        pixels[1, 1] = dark_red    # shadow
        pixels[2, 1] = mid_red     # neither
        pixels[3, 1] = bright_red  # highlight

        doc = Document()
        doc.image = img

        analysis = self.wb.analyze(doc)

        shadow_region = analysis.get_region("shadow")
        highlight_region = analysis.get_region("highlight")

        self.assertIn((1, 1), shadow_region)
        self.assertNotIn((2, 1), shadow_region)
        self.assertNotIn((3, 1), shadow_region)

        self.assertIn((3, 1), highlight_region)
        self.assertNotIn((2, 1), highlight_region)
        self.assertNotIn((1, 1), highlight_region)

    def test_workbench_select_region(self):
        img = Image.new("RGBA", (16, 15), (0, 0, 0, 0))
        pixels = img.load()
        pixels[0, 0] = (255, 0, 0, 255)

        doc = Document()
        doc.image = img
        self.wb.open_document(doc)

        head_region = self.wb.select_region("head")
        self.assertIn((0, 0), head_region)

if __name__ == "__main__":
    unittest.main()
