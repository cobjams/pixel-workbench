import unittest
from PIL import Image
from pixel_workbench.core.document import Document
from pixel_workbench.analysis.sprite_analysis import SpriteAnalysis
from pixel_workbench.analysis.repair.engine import RepairEngine
from pixel_workbench.analysis.repair.rules import RemoveIsolatedPixelsRule, StandardizeOutlineColorRule, NormalizePaletteRule

class TestRepairEngine(unittest.TestCase):
    def setUp(self):
        # Create a blank document
        self.doc = Document()
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        self.doc.image = img

    def test_remove_isolated_pixels(self):
        rule = RemoveIsolatedPixelsRule(max_pixels=1)
        pixels = self.doc.image.load()

        # Draw a 2x2 square (not isolated)
        pixels[2, 2] = (255, 0, 0, 255)
        pixels[2, 3] = (255, 0, 0, 255)
        pixels[3, 2] = (255, 0, 0, 255)
        pixels[3, 3] = (255, 0, 0, 255)

        # Draw an isolated pixel
        pixels[10, 10] = (0, 255, 0, 255)

        analysis = SpriteAnalysis(self.doc.image)

        self.assertTrue(rule.applies(self.doc, analysis))
        rule.repair(self.doc, analysis)

        pixels = self.doc.image.load()
        self.assertEqual(pixels[2, 2], (255, 0, 0, 255))
        self.assertEqual(pixels[3, 3], (255, 0, 0, 255))
        self.assertEqual(pixels[10, 10], (0, 0, 0, 0))

        self.assertEqual(rule.explain(), "Removed 1 isolated stray pixels.")

    def test_standardize_outline_color(self):
        rule = StandardizeOutlineColorRule()
        pixels = self.doc.image.load()

        # Draw a 3x3 square with outline
        # Core
        pixels[2, 2] = (200, 200, 200, 255)
        # Outline (mostly black, one red pixel)
        pixels[1, 1] = (0, 0, 0, 255)
        pixels[1, 2] = (0, 0, 0, 255)
        pixels[1, 3] = (0, 0, 0, 255)
        pixels[2, 1] = (0, 0, 0, 255)
        pixels[2, 3] = (0, 0, 0, 255)
        pixels[3, 1] = (0, 0, 0, 255)
        pixels[3, 2] = (255, 0, 0, 255) # Rogue red outline pixel
        pixels[3, 3] = (0, 0, 0, 255)

        analysis = SpriteAnalysis(self.doc.image)

        self.assertTrue(rule.applies(self.doc, analysis))
        rule.repair(self.doc, analysis)

        pixels = self.doc.image.load()
        self.assertEqual(pixels[1, 1], (0, 0, 0, 255))
        self.assertEqual(pixels[3, 2], (0, 0, 0, 255)) # Red pixel should be standardized to black
        self.assertEqual(pixels[2, 2], (200, 200, 200, 255)) # Core should remain the same

        self.assertEqual(rule.explain(), "Standardized outline color to #000000.")

    def test_normalize_palette(self):
        rule = NormalizePaletteRule(threshold=10.0)
        pixels = self.doc.image.load()

        # Draw main color
        for x in range(4):
            for y in range(4):
                pixels[x, y] = (100, 100, 100, 255)

        # Draw near-duplicate color (few instances)
        pixels[0, 0] = (105, 100, 100, 255)
        pixels[1, 0] = (105, 100, 100, 255)

        analysis = SpriteAnalysis(self.doc.image)

        self.assertTrue(rule.applies(self.doc, analysis))
        rule.repair(self.doc, analysis)

        pixels = self.doc.image.load()
        self.assertEqual(pixels[0, 0], (100, 100, 100, 255))
        self.assertEqual(pixels[2, 2], (100, 100, 100, 255))

        self.assertEqual(rule.explain(), "Merged near-duplicate colors in the palette.")

    def test_repair_engine(self):
        engine = RepairEngine()
        pixels = self.doc.image.load()

        # Add isolated pixel
        pixels[10, 10] = (0, 255, 0, 255)

        report = engine.run(self.doc)

        self.assertTrue(report["repaired"])
        self.assertTrue(len(report["actions"]) > 0)
        self.assertIn("Removed 1 isolated stray pixels.", report["actions"])

if __name__ == "__main__":
    unittest.main()
