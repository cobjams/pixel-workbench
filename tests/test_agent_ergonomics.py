import unittest
import os
import json
import subprocess
from PIL import Image

from pixel_workbench.app import Workbench
from pixel_workbench.core.document import Document
from pixel_workbench.analysis.adapters.agent import CodingAgentProvider
from pixel_workbench.analysis.repair.engine import RepairEngine
from pixel_workbench.analysis.repair.rules import RemoveJaggiesRule
from pixel_workbench.tools.mcp_server import AgentToolServer


class TestAgentErgonomicsAndPhases(unittest.TestCase):
    def setUp(self):
        self.wb = Workbench()
        self.provider = CodingAgentProvider()

    def test_ascii_grid_roundtrip(self):
        ws = self.provider.construct_sprite(prompt="test potion", size=(8, 8))
        grid = """
        ...##...
        ...##...
        ..#BB#..
        .#BhhB#.
        .#BBBB#.
        .#BssB#.
        ..####..
        ........
        """
        legend = {
            "#": "#000000",
            "B": "#3366cc",
            "h": "#88bbff",
            "s": "#113377",
        }
        ws.apply_ascii_grid(grid, legend)
        exported = ws.to_ascii_grid(include_legend=True)

        self.assertEqual(exported["width"], 8)
        self.assertEqual(exported["height"], 8)
        self.assertEqual(len(exported["grid"]), 8)
        # Verify top transparent corners and middle pixels
        self.assertEqual(exported["grid"][0][:3], "...")
        self.assertEqual(ws.document.image.getpixel((3, 0)), (0, 0, 0, 255))
        self.assertEqual(ws.document.image.getpixel((3, 3)), (136, 187, 255, 255))

        # Verify summary() is 100% JSON serializable
        summary_json = json.dumps(ws.summary(include_grid=True))
        parsed = json.loads(summary_json)
        self.assertEqual(parsed["analysis"]["palette_count"], 4)

    def test_high_level_primitives_and_outline(self):
        ws = self.provider.construct_sprite(prompt="shield", size=(12, 12))
        wb = ws.workbench

        # Draw filled interior rectangle and outline it deterministically
        wb.draw_rect(3, 3, 8, 8, "#cc3333", fill=True)
        wb.generate_outline(color="#111111", mode="outside")
        wb.apply_shading(light_dir="top_left", intensity=0.25)

        ws.refresh()
        # Outline should sit at (2, 3..8), (9, 3..8), (3..8, 2), (3..8, 9)
        self.assertEqual(ws.document.image.getpixel((2, 5)), (17, 17, 17, 255))
        # Top-left interior pixel (3, 3) should be brighter than bottom-right interior pixel (8, 8)
        tl = ws.document.image.getpixel((3, 3))
        br = ws.document.image.getpixel((8, 8))
        self.assertGreater(tl[0], br[0])

    def test_draw_line_ellipse_flood_fill(self):
        ws = self.provider.construct_sprite(prompt="shapes", size=(10, 10))
        wb = ws.workbench

        wb.draw_ellipse(1, 1, 8, 8, "#000000", fill=False)
        wb.flood_fill(4, 4, "#00cc66")
        wb.draw_line(0, 0, 9, 9, "#ffffff")

        self.assertEqual(ws.document.image.getpixel((5, 3)), (0, 204, 102, 255))
        self.assertEqual(ws.document.image.getpixel((0, 0)), (255, 255, 255, 255))
        self.assertEqual(ws.document.image.getpixel((9, 9)), (255, 255, 255, 255))

    def test_color_ramp_generation(self):
        ramp = self.wb.generate_color_ramp("#3366cc", steps=4)
        self.assertEqual(len(ramp), 4)
        self.assertTrue(all(c.startswith("#") and len(c) == 7 for c in ramp))

    def test_jaggies_detection_and_repair_undo(self):
        ws = self.provider.construct_sprite(prompt="jaggy test", size=(8, 8))
        # Construct an L-corner double on the top-left of a block
        grid = """
        ........
        .#####..
        .#RRRR#.
        .#RRRR#.
        .#RRRR#.
        ..####..
        ........
        ........
        """
        ws.apply_ascii_grid(grid, {"#": "#000000", "R": "#ff0000"})

        rule = RemoveJaggiesRule()
        self.assertTrue(rule.applies(ws.document, ws.analysis))

        # Run repair engine with jaggies rule and verify undo works
        engine = RepairEngine(include_jaggies=True)
        report = engine.run(ws.document)
        self.assertTrue(report["repaired"])
        self.assertEqual(ws.document.image.getpixel((1, 1)), (0, 0, 0, 0))

        # Undo should restore the pixel at (1, 1)
        self.assertTrue(ws.workbench.undo())
        self.assertEqual(ws.document.image.getpixel((1, 1)), (0, 0, 0, 255))

    def test_compare_and_alpha_quantize(self):
        from pixel_workbench.analysis.palette_matcher import quantize_to_palette

        img1 = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        img1.putpixel((2, 2), (250, 10, 10, 255))
        img2 = img1.copy()
        img2.putpixel((3, 3), (10, 10, 250, 255))

        doc1, doc2 = Document(), Document()
        doc1.image, doc2.image = img1, img2

        diff = self.wb.compare(doc1, doc2)
        self.assertEqual(diff["changed_pixels"], 1)
        self.assertGreater(diff["similarity_score"], 0.9)

        # Quantize while preserving transparency info
        q_img = quantize_to_palette(img1, [(255, 0, 0), (0, 0, 255)])
        self.assertEqual(q_img.mode, "P")
        self.assertIn("transparency", q_img.info)

    def test_frames_slice_and_assemble(self):
        f1 = Image.new("RGBA", (8, 8), (255, 0, 0, 255))
        f2 = Image.new("RGBA", (8, 8), (0, 255, 0, 255))
        sheet = Document.assemble_sprite_sheet([f1, f2], columns=2)
        self.assertEqual(sheet.size, (16, 8))

        sliced = sheet.slice_frames(8, 8)
        self.assertEqual(len(sliced), 2)
        self.assertEqual(sliced[0].image.getpixel((0, 0)), (255, 0, 0, 255))
        self.assertEqual(sliced[1].image.getpixel((0, 0)), (0, 255, 0, 255))

    def test_mcp_agent_tool_server(self):
        server = AgentToolServer()
        schemas = server.get_tool_schemas()
        self.assertGreaterEqual(len(schemas), 7)

        res1 = server.call_tool("init_workspace", {"width": 8, "height": 8, "prompt": "gem"})
        self.assertEqual(res1["analysis"]["size"], [8, 8])

        res2 = server.call_tool("draw_shape", {
            "shape": "rect", "x0": 2, "y0": 2, "x1": 5, "y1": 5, "color": "#2288ff", "fill": True
        })
        self.assertEqual(res2["analysis"]["palette_count"], 1)

        res3 = server.call_tool("auto_outline_and_shade", {
            "outline_color": "#000000", "outline_mode": "outside", "apply_shading": True
        })
        self.assertGreater(res3["analysis"]["outline_pixel_count"], 0)

    def test_cli_analyze_and_grid(self):
        tmp_png = "test_cli_analyze.png"
        try:
            img = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
            img.putpixel((1, 1), (255, 0, 0, 255))
            img.save(tmp_png)

            res = subprocess.run(
                ["python3", "-m", "pixel_workbench", "analyze", tmp_png],
                capture_output=True, text=True, check=True
            )
            data = json.loads(res.stdout)
            self.assertEqual(data["size"], [4, 4])
            self.assertIn("ascii_representation", data)
        finally:
            if os.path.exists(tmp_png):
                os.remove(tmp_png)


if __name__ == "__main__":
    unittest.main()
