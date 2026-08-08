import unittest
from PIL import Image
import os
import subprocess
import json
from pixel_workbench.app import Workbench
from pixel_workbench.analysis.draft import SpriteDraft
from pixel_workbench.analysis.adapters.stub import StubProvider
from pixel_workbench.analysis.adapters.agent import CodingAgentProvider

class TestCapabilities(unittest.TestCase):
    def setUp(self):
        self.wb = Workbench()

    def test_construct_draft(self):
        draft = self.wb.construct(prompt="test prompt", size=(16, 16))
        self.assertIsInstance(draft, SpriteDraft)
        self.assertEqual(draft.prompt, "test prompt")
        self.assertEqual(draft.document.width, 16)
        self.assertEqual(draft.document.height, 16)

    def test_coding_agent_provider(self):
        from pixel_workbench.analysis.workspace import SpriteWorkspace
        self.wb.engine.provider = CodingAgentProvider()
        workspace = self.wb.construct(prompt="build base layer", size=(32, 32))
        self.assertIsInstance(workspace, SpriteWorkspace)
        self.assertEqual(workspace.document.width, 32)
        # Verify it starts blank
        self.assertEqual(workspace.document.image.getpixel((0,0)), (0,0,0,0))

    def test_review_sprite(self):
        draft = self.wb.construct(prompt="test", size=(32, 32))
        report = self.wb.review(draft, expected_size=(32, 32))

        self.assertIn("validation_passed", report)
        self.assertTrue(report["validation_passed"])

        # Test failing review (wrong dimensions)
        report2 = self.wb.review(draft, expected_size=(16, 16))
        self.assertFalse(report2["validation_passed"])
        self.assertTrue(any("dimensions" in w for w in report2["warnings"]))

    def test_analyze(self):
        # Create a dummy image to analyze
        dummy_path = "dummy_test_image.png"
        img = Image.new("RGBA", (16, 16), (255, 0, 0, 255))
        img.save(dummy_path)

        try:
            # When analyzing a single image path, it returns a SpriteAnalysis
            result = self.wb.analyze(dummy_path)
            self.assertEqual(result.transparency_percentage, 0.0)
            self.assertEqual(len(result.palette), 1)
            self.assertEqual(result.palette[0], (255, 0, 0, 255))
        finally:
            if os.path.exists(dummy_path):
                os.remove(dummy_path)

    def test_sprite_analysis_properties(self):
        # Create a test shape
        img = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
        pixels = img.load()

        # Draw a 2x2 red square in the middle
        pixels[1, 1] = (255, 0, 0, 255)
        pixels[2, 1] = (255, 0, 0, 255)
        pixels[1, 2] = (255, 0, 0, 255)
        pixels[2, 2] = (255, 0, 0, 255)

        from pixel_workbench.core.document import Document
        doc = Document()
        doc.image = img

        analysis = self.wb.analyze(doc)

        self.assertEqual(analysis.transparency_percentage, 75.0)
        self.assertEqual(analysis.palette, [(255, 0, 0, 255)])
        self.assertEqual(len(analysis.connected_components), 1)
        self.assertEqual(analysis.connected_components[0], {(1, 1), (1, 2), (2, 1), (2, 2)})
        self.assertEqual(analysis.outline, {(1, 1), (1, 2), (2, 1), (2, 2)})
        self.assertEqual(analysis.symmetry["horizontal"], 1.0)
        self.assertEqual(analysis.symmetry["vertical"], 1.0)

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
            # We access the raw engine utilities directly since palette_matcher
            # hasn't been mapped to a top level Workbench capability yet in the refactor.
            from pixel_workbench.analysis.palette_matcher import match_palette, quantize_to_palette

            palette = match_palette(target_img, dummy_path)
            self.assertEqual(len(palette), 2)
            self.assertIn((255, 0, 0), palette)

            quantized = quantize_to_palette(target_img, palette)
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
                ["python", "-m", "pixel_workbench", "construct", "--prompt", "test", "--output", output_file],
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
