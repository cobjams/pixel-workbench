import io
import json
import os
import unittest
from PIL import Image

from pixel_workbench.app import Workbench
from pixel_workbench.core.document import Document
from pixel_workbench.core.commands import ApplyAsciiGrid
from pixel_workbench.analysis.sprite_analysis import SpriteAnalysis
from pixel_workbench.analysis.adapters.agent import CodingAgentProvider
from pixel_workbench.analysis.repair.engine import RepairEngine
from pixel_workbench.analysis.regression import (
    check_grid_roundtrip,
    check_palette_regression,
    check_outline_regression,
    check_symmetry_validation,
    check_animation_regression,
    check_repair_regression,
    generate_regression_report,
)
from pixel_workbench.tools.mcp_server import AgentToolServer, MCPStdioClient


class TestPriority1GridRoundTrip(unittest.TestCase):
    def setUp(self):
        self.provider = CodingAgentProvider()

    def test_space_whitespace_and_blank_rows_preserved(self):
        """Verify leading/trailing spaces and blank rows are never silently stripped."""
        ws = self.provider.construct_sprite(prompt="whitespace test", size=(6, 4))
        # Row 0 is all spaces (blank row), Row 1 has 2 leading & 2 trailing spaces, Row 2 has 1 leading space
        grid_str = "\n".join([
            "      ",
            "  ##  ",
            " #RR# ",
            "      ",
        ])
        ws.apply_ascii_grid(grid_str, {"#": "#000000", "R": "#ff0000"})

        # Row 0 must be completely transparent
        for x in range(6):
            self.assertEqual(ws.document.image.getpixel((x, 0)), (0, 0, 0, 0))

        # Row 1 must have black pixels at x=2, 3 and transparent at x=0, 1, 4, 5
        self.assertEqual(ws.document.image.getpixel((0, 1)), (0, 0, 0, 0))
        self.assertEqual(ws.document.image.getpixel((1, 1)), (0, 0, 0, 0))
        self.assertEqual(ws.document.image.getpixel((2, 1)), (0, 0, 0, 255))
        self.assertEqual(ws.document.image.getpixel((3, 1)), (0, 0, 0, 255))
        self.assertEqual(ws.document.image.getpixel((4, 1)), (0, 0, 0, 0))

        # Row 2 must have black at x=1,4 and red at x=2,3
        self.assertEqual(ws.document.image.getpixel((1, 2)), (0, 0, 0, 255))
        self.assertEqual(ws.document.image.getpixel((2, 2)), (255, 0, 0, 255))
        self.assertEqual(ws.document.image.getpixel((3, 2)), (255, 0, 0, 255))
        self.assertEqual(ws.document.image.getpixel((4, 2)), (0, 0, 0, 255))

    def test_image_to_ascii_to_image_exact_roundtrip(self):
        """Verify Image -> ASCII Grid -> Image produces 100% identical pixels including partial alpha and >100 colors."""
        img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        px = img.load()
        # Populate 120 unique RGBA colors (including semi-transparent pixels) leaving transparent borders
        color_idx = 0
        for y in range(2, 14):
            for x in range(2, 12):
                r = (color_idx * 17) % 256
                g = (color_idx * 31) % 256
                b = (color_idx * 47) % 256
                a = 128 if (color_idx % 5 == 0) else 255
                px[x, y] = (r, g, b, a)
                color_idx += 1

        doc = Document()
        doc.image = img
        doc.original_mode = "RGBA"

        rt_result = check_grid_roundtrip(doc)
        self.assertTrue(rt_result["passed"])
        self.assertEqual(rt_result["changed_pixels"], 0)

    def test_strict_grid_validation(self):
        """Verify strict=True rejects ragged rows and out-of-bounds grids."""
        ws = self.provider.construct_sprite(prompt="strict", size=(4, 4))
        with self.assertRaises(ValueError):
            ws.apply_ascii_grid(["..#.", "..."], {"#": "#000000"}, strict=True)
        with self.assertRaises(ValueError):
            ws.apply_ascii_grid(["....."], {"#": "#000000"}, strict=True)


class TestPriority2RepairSafety(unittest.TestCase):
    def setUp(self):
        self.provider = CodingAgentProvider()

    def test_preserves_interior_eyes_symmetric_sparks_and_outline_accents(self):
        """
        Verify RepairEngine(safe=True) preserves:
          - 1px interior eyes/highlights
          - 1px symmetric detached sparks/stars
          - 2+ pixel selective-outline (sel-out) accents
        while still removing a 1px asymmetric stray pixel and a 1px rogue outline pixel.
        """
        ws = self.provider.construct_sprite(prompt="character with eyes, sparks, crown accent", size=(10, 10))
        # '.' = transparent
        # '#' = black outline (#000000)
        # 'G' = 3px gold crown accent on top outline (#ffcc00) -> should be PRESERVED
        # 'E' = 1px rogue red outline error at (7, 5) (#ff0000) -> should be FIXED to #000000
        # 'B' = blue face interior (#3366cc)
        # 'W' = 1px white eyes inside face at (3, 4) and (6, 4) (#ffffff) -> should be PRESERVED
        # 'S' = symmetric 1px floating cyan sparks at (0, 2) and (9, 2) (#00ffff) -> should be PRESERVED
        # 'X' = asymmetric 1px stray noise at (0, 8) (#00ff00) -> should be REMOVED
        grid = [
            "..........",
            "...#GG#...",
            "S.#BBBB#.S",
            "..#BWWB#..",
            "..#BBBB#..",
            "..#BBBBE..",
            "...####...",
            "..........",
            "X.........",
            "..........",
        ]
        legend = {
            "#": "#000000",
            "G": "#ffcc00",
            "E": "#ff0000",
            "B": "#3366cc",
            "W": "#ffffff",
            "S": "#00ffff",
            "X": "#00ff00",
        }
        ws.apply_ascii_grid(grid, legend, preserve_whitespace=True, strict=True)

        # First test dry_run=True: should report changes without mutating image
        dry_report = ws.workbench.repair(dry_run=True, safe=True)
        self.assertTrue(dry_report["repaired"])
        self.assertTrue(dry_report["dry_run"])
        # Stray pixel X at (0, 8) should still be there after dry_run
        self.assertEqual(ws.document.image.getpixel((0, 8)), (0, 255, 0, 255))

        # Now run actual safe repair
        live_report = ws.workbench.repair(dry_run=False, safe=True)
        self.assertTrue(live_report["repaired"])

        px = ws.document.image.load()
        # 1. Asymmetric stray noise 'X' at (0, 8) was removed
        self.assertEqual(px[0, 8], (0, 0, 0, 0))
        # 2. Symmetric sparks 'S' at (0, 2) and (9, 2) were preserved!
        self.assertEqual(px[0, 2], (0, 255, 255, 255))
        self.assertEqual(px[9, 2], (0, 255, 255, 255))
        # 3. Interior 1px white eyes 'W' at (4, 3) and (5, 3) were preserved!
        self.assertEqual(px[4, 3], (255, 255, 255, 255))
        self.assertEqual(px[5, 3], (255, 255, 255, 255))
        # 4. 2px Gold crown outline accent 'G' at (4..5, 1) was preserved!
        self.assertEqual(px[4, 1], (255, 204, 0, 255))
        self.assertEqual(px[5, 1], (255, 204, 0, 255))
        # 5. 1px Rogue red outline pixel 'E' at (7, 5) was standardized to black!
        self.assertEqual(px[7, 5], (0, 0, 0, 255))


class TestPriority3MCPProtocolIntegration(unittest.TestCase):
    def test_mcp_stdio_client_server_end_to_end(self):
        """
        Spawns the real MCP stdio server in a subprocess and exercises:
          1. initialize + notifications/initialized handshake
          2. tools/list discovery
          3. tools/call across the agent workflow (including multimodal image preview)
          4. structured error responses for unknown tools and invalid arguments
        """
        out_path = "/workspace/gentle-curie/test_mcp_e2e_out.png"
        try:
            with MCPStdioClient() as client:
                # 1. Initialize handshake (including instructions, resources, prompts capabilities)
                init_res = client.initialize()
                self.assertEqual(init_res["serverInfo"]["name"], "pixel-workbench")
                self.assertIn("tools", init_res["capabilities"])
                self.assertIn("resources", init_res["capabilities"])
                self.assertIn("prompts", init_res["capabilities"])
                self.assertIn("instructions", init_res)
                self.assertIn("6-step", init_res["instructions"])

                # 2. Discover tools, annotations, resources, and prompts
                tools = client.list_tools()
                tool_names = {t["name"] for t in tools}
                self.assertIn("init_workspace", tool_names)
                self.assertIn("apply_ascii_grid", tool_names)
                self.assertIn("transform_sprite", tool_names)
                self.assertIn("undo_redo", tool_names)
                self.assertIn("inspect_animation", tool_names)
                self.assertIn("regression_report", tool_names)
                self.assertIn("lint_and_repair", tool_names)
                for t in tools:
                    self.assertIn("annotations", t)
                    self.assertIn("readOnlyHint", t["annotations"])

                resources = client.list_resources()
                res_uris = {r["uri"] for r in resources}
                self.assertIn("sprite://current/summary", res_uris)
                self.assertIn("sprite://current/grid", res_uris)

                prompts = client.list_prompts()
                prompt_names = {p["name"] for p in prompts}
                self.assertIn("construct-sprite", prompt_names)
                self.assertIn("audit-animation", prompt_names)
                p_detail = client.get_prompt("construct-sprite", {"subject": "shield", "size": "16x16"})
                self.assertIn("shield", p_detail["description"])

                # 3. Execute workflow: init -> checkpoint -> draw -> transform -> undo/redo -> outline -> regression_report -> save
                r_init = client.call_tool("init_workspace", {"width": 8, "height": 8, "prompt": "mcp gem"})
                self.assertFalse(r_init["isError"])
                self.assertEqual(r_init["data"]["analysis"]["size"], [8, 8])

                # Read MCP resource for current grid
                grid_res = client.read_resource("sprite://current/grid")
                self.assertEqual(grid_res[0]["uri"], "sprite://current/grid")

                r_draw = client.call_tool(
                    "draw_shape",
                    {"shape": "rect", "x0": 2, "y0": 2, "x1": 5, "y1": 5, "color": "#2266dd", "fill": True},
                    include_preview_image=True,
                )
                self.assertFalse(r_draw["isError"])
                # Verify multimodal image content was returned alongside text
                content_types = [c["type"] for c in r_draw["raw_content"]]
                self.assertIn("text", content_types)
                self.assertIn("image", content_types)

                # Test transform_sprite + undo_redo
                r_paint = client.call_tool(
                    "transform_sprite",
                    {"operation": "paint_pixel", "x": 0, "y": 0, "color": "#ff0000"},
                )
                self.assertFalse(r_paint["isError"])
                self.assertIn("#ff0000", r_paint["data"]["analysis"]["palette"])

                r_undo = client.call_tool("undo_redo", {"action": "undo"})
                self.assertFalse(r_undo["isError"])
                self.assertTrue(r_undo["data"]["applied"])
                self.assertNotIn("#ff0000", r_undo["data"]["analysis"]["palette"])

                r_redo = client.call_tool("undo_redo", {"action": "redo"})
                self.assertFalse(r_redo["isError"])
                self.assertTrue(r_redo["data"]["applied"])
                self.assertIn("#ff0000", r_redo["data"]["analysis"]["palette"])

                # Undo the stray red pixel before continuing
                client.call_tool("undo_redo", {"action": "undo"})

                r_cp = client.call_tool("checkpoint_workspace", {"name": "after_box"})
                self.assertFalse(r_cp["isError"])
                self.assertIn("after_box", r_cp["data"]["available_checkpoints"])

                r_out = client.call_tool(
                    "auto_outline_and_shade",
                    {"outline_color": "#000000", "outline_mode": "outside", "apply_shading": True},
                )
                self.assertFalse(r_out["isError"])

                r_reg = client.call_tool("regression_report", {"checkpoint_name": "after_box"})
                self.assertFalse(r_reg["isError"])
                self.assertIn("qa_suite", r_reg["data"])
                self.assertTrue(r_reg["data"]["qa_suite"]["tests"]["grid_roundtrip"]["passed"])
                self.assertTrue(r_reg["data"]["qa_suite"]["tests"]["symmetry_validation"]["passed"])

                r_save = client.call_tool("save_sprite", {"filepath": out_path})
                self.assertFalse(r_save["isError"])
                self.assertTrue(os.path.exists(out_path))

                # Test inspect_animation + shift_region on a 2-frame (16x8) strip in a second workspace_id
                client.call_tool("init_workspace", {"width": 16, "height": 8, "workspace_id": "anim_ws"})
                client.call_tool(
                    "draw_shape",
                    {"shape": "rect", "x0": 2, "y0": 2, "x1": 5, "y1": 5, "color": "#2266dd", "workspace_id": "anim_ws"},
                )
                # Frame 1 (x=8..15) is shifted 2px left (at x=8..11 instead of 10..13)
                client.call_tool(
                    "draw_shape",
                    {"shape": "rect", "x0": 8, "y0": 2, "x1": 11, "y1": 5, "color": "#2266dd", "workspace_id": "anim_ws"},
                )
                r_anim_before = client.call_tool(
                    "inspect_animation",
                    {"frame_width": 8, "frame_height": 8, "max_anchor_shift": 0.5, "workspace_id": "anim_ws"},
                )
                self.assertFalse(r_anim_before["isError"])
                self.assertFalse(r_anim_before["data"]["passed"])
                self.assertEqual(r_anim_before["data"]["max_anchor_shift"], 2.0)

                # Shift Frame 1 region [8, 0, 16, 8] by dx=+2
                client.call_tool(
                    "transform_sprite",
                    {"operation": "shift_region", "dx": 2, "dy": 0, "left": 8, "upper": 0, "right": 16, "lower": 8, "workspace_id": "anim_ws"},
                )
                r_anim_after = client.call_tool(
                    "inspect_animation",
                    {"frame_width": 8, "frame_height": 8, "max_anchor_shift": 0.5, "workspace_id": "anim_ws"},
                )
                self.assertFalse(r_anim_after["isError"])
                self.assertTrue(r_anim_after["data"]["passed"])
                self.assertEqual(r_anim_after["data"]["max_anchor_shift"], 0.0)

                # 4. Structured error responses
                r_unknown = client.call_tool("non_existent_tool", {})
                self.assertTrue(r_unknown["isError"])
                self.assertEqual(r_unknown["data"]["error_type"], "UnknownToolError")

                r_bad_args = client.call_tool("init_workspace", {"width": -5, "height": 8})
                self.assertTrue(r_bad_args["isError"])
                self.assertEqual(r_bad_args["data"]["error_type"], "ValueError")

                r_missing_xy1 = client.call_tool(
                    "draw_shape",
                    {"shape": "rect", "x0": 0, "y0": 0, "color": "#ff0000"},
                )
                self.assertTrue(r_missing_xy1["isError"])
                self.assertEqual(r_missing_xy1["data"]["error_type"], "ValueError")
                self.assertIn("x1", r_missing_xy1["data"]["error"])
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    def test_content_length_framing_and_malformed_json(self):
        """Verify the stdio loop also handles Content-Length framing and JSON parse errors."""
        server = AgentToolServer()
        ping_body = json.dumps({"jsonrpc": "2.0", "id": 42, "method": "ping"})
        framed_input = (
            f"Content-Length: {len(ping_body)}\r\n\r\n{ping_body}\n"
            "{malformed_json\n"
        )
        in_buf = io.StringIO(framed_input)
        out_buf = io.StringIO()
        server.serve_stdio(in_stream=in_buf, out_stream=out_buf)

        output = out_buf.getvalue()
        self.assertIn("Content-Length:", output)
        self.assertIn('"id": 42', output)
        self.assertIn("-32700", output)


class TestPriority4PixelArtQARegressionSuite(unittest.TestCase):
    def setUp(self):
        self.provider = CodingAgentProvider()

    def test_qa_suite_detects_palette_outline_and_symmetry_regressions(self):
        ws = self.provider.construct_sprite(
            prompt="symmetric shield",
            size=(8, 8),
            constraints={
                "allowed_palette": ["#000000", "#3366cc"],
                "max_colors": 2,
                "allow_new_colors": False,
                "expected_outline_color": "#000000",
                "preserve_symmetry": True,
            },
        )
        grid = [
            "........",
            "..####..",
            ".#BBBB#.",
            ".#BBBB#.",
            ".#BBBB#.",
            ".#BBBB#.",
            "..####..",
            "........",
        ]
        ws.apply_ascii_grid(grid, {"#": "#000000", "B": "#3366cc"}, strict=True)
        ws.checkpoint("clean_shield")

        # Verify clean state passes 100% of QA checks
        clean_report = ws.regression_report("clean_shield")
        self.assertTrue(clean_report["passed"])

        # Now introduce an asymmetric hole in the outline AND an unauthorized color (#ff00ff)
        ws.workbench.paint_color(1, 2, "#ff00ff")
        bad_report = ws.regression_report("clean_shield")

        self.assertFalse(bad_report["passed"])
        tests = bad_report["qa_suite"]["tests"]
        self.assertTrue(tests["grid_roundtrip"]["passed"])
        self.assertFalse(tests["palette_regression"]["passed"])
        self.assertIn("#ff00ff", tests["palette_regression"]["unexpected_colors"])
        self.assertFalse(tests["outline_regression"]["passed"])
        self.assertIn([1, 2], tests["outline_regression"]["outline_leaks"])
        self.assertFalse(tests["symmetry_validation"]["passed"])

    def test_animation_regression_check(self):
        f1 = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        f2 = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        for y in range(2, 6):
            for x in range(2, 6):
                f1.putpixel((x, y), (255, 0, 0, 255))
                f2.putpixel((x, y + 1), (255, 0, 0, 255))  # 1px bob down

        good_anim = check_animation_regression([f1, f2])
        self.assertTrue(good_anim["passed"])
        self.assertEqual(good_anim["max_center_of_mass_shift"], 1.0)

        # Introduce unexpected palette color in frame 2
        f2_bad = f2.copy()
        f2_bad.putpixel((3, 3), (0, 255, 0, 255))
        bad_anim = check_animation_regression([f1, f2_bad])
        self.assertFalse(bad_anim["passed"])
        self.assertEqual(len(bad_anim["palette_drifts"]), 1)

        # Verify configurable anchor-point validation detects excessive ground-anchor drift
        f2_shifted = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        for y in range(2, 6):
            for x in range(4, 8):  # shifted 2px right
                f2_shifted.putpixel((x, y), (255, 0, 0, 255))
        strict_anchor = check_animation_regression([f1, f2_shifted], anchor="bottom_center", max_anchor_shift=1.0)
        self.assertFalse(strict_anchor["passed"])
        self.assertEqual(strict_anchor["max_anchor_shift"], 2.0)


if __name__ == "__main__":
    unittest.main()
