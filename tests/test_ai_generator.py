import unittest
from PIL import Image
import os
import subprocess
import json
from pixel_workbench.app import Workbench
from pixel_workbench.ai.draft import SpriteDraft
from pixel_workbench.ai.adapters.stub import StubProvider

class TestAIGenerator(unittest.TestCase):
    def setUp(self):
        self.wb = Workbench()

    def test_generate_draft(self):
        draft = self.wb.ai.generate_sprite(prompt="test prompt", size=(16, 16))
        self.assertIsInstance(draft, SpriteDraft)
        self.assertEqual(draft.prompt, "test prompt")
        self.assertEqual(draft.document.width, 16)
        self.assertEqual(draft.document.height, 16)

    def test_review_sprite(self):
        draft = self.wb.ai.generate_sprite(prompt="test", size=(32, 32))
        report = self.wb.ai.review_sprite(draft, expected_size=(32, 32))

        self.assertIn("validation_passed", report)
        self.assertTrue(report["validation_passed"])

        # Test failing review (wrong dimensions)
        report2 = self.wb.ai.review_sprite(draft, expected_size=(16, 16))
        self.assertFalse(report2["validation_passed"])
        self.assertTrue(any("dimensions" in w for w in report2["warnings"]))

    def test_style_analyzer(self):
        # Create a dummy image to analyze
        dummy_path = "dummy_test_image.png"
        img = Image.new("RGBA", (16, 16), (255, 0, 0, 255))
        img.save(dummy_path)

        try:
            result = self.wb.ai.analyze_style(dummy_path)
            self.assertEqual(result["sprite_count"], 1)
            self.assertEqual(result["common_sizes"][0], [16, 16])
            self.assertEqual(result["average_palette_size"], 1) # Only red color
        finally:
            if os.path.exists(dummy_path):
                os.remove(dummy_path)

    def test_palette_matcher(self):
        dummy_path = "dummy_palette_ref.png"
        img = Image.new("P", (16, 16))
        # Add red and blue to palette
        flat_palette = [255, 0, 0, 0, 0, 255] + [0] * 762
        img.putpalette(flat_palette)

        # We need to use the indices so getcolors() can find them
        pixels = img.load()
        pixels[0, 0] = 0 # red
        pixels[1, 0] = 1 # blue

        img.save(dummy_path)

        # Image to quantize (mostly red)
        target_img = Image.new("RGB", (16, 16), (250, 10, 10))

        try:
            palette = self.wb.ai.match_palette(target_img, dummy_path)
            self.assertEqual(len(palette), 2)
            self.assertIn((255, 0, 0), palette)

            quantized = self.wb.ai.quantize_to_palette(target_img, palette)
            self.assertEqual(quantized.mode, "P")
            self.assertEqual(quantized.getpalette()[:6], [255, 0, 0, 0, 0, 255])
        finally:
            if os.path.exists(dummy_path):
                os.remove(dummy_path)

    def test_cli(self):
        # Test that CLI headless mode runs without errors
        output_file = "test_cli_output.png"
        try:
            result = subprocess.run(
                ["python", "-m", "pixel_workbench", "ai", "generate", "--prompt", "test", "--output", output_file],
                capture_output=True, text=True, check=True
            )
            # Try to parse the json response
            data = json.loads(result.stdout)
            self.assertEqual(data["prompt"], "test")
            self.assertTrue(os.path.exists(output_file))
        finally:
            if os.path.exists(output_file):
                os.remove(output_file)

if __name__ == "__main__":
    unittest.main()
