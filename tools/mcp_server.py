import json
import sys
from typing import Dict, Any, Optional
from PIL import Image

from ..core.document import Document
from ..analysis.workspace import SpriteWorkspace
from ..analysis.adapters.agent import CodingAgentProvider


class AgentToolServer:
    """
    Model Context Protocol (MCP) & JSON-RPC compatible tool server interface
    for autonomous coding agents working with Pixel Workbench.
    """
    def __init__(self):
        self.provider = CodingAgentProvider()
        self.workspace: Optional[SpriteWorkspace] = None

    def get_tool_schemas(self):
        """Returns the list of tool definitions in MCP / JSON-Schema format."""
        return [
            {
                "name": "init_workspace",
                "description": "Initialize a new blank sprite workspace or open an existing image file.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "width": {"type": "integer", "default": 16},
                        "height": {"type": "integer", "default": 16},
                        "filepath": {"type": "string", "description": "Optional path to existing PNG"},
                        "prompt": {"type": "string", "default": ""},
                    },
                },
            },
            {
                "name": "inspect_sprite",
                "description": "Returns the semantic analysis, validation report, and 2D ASCII character grid of the active sprite.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "include_grid": {"type": "boolean", "default": True}
                    },
                },
            },
            {
                "name": "apply_ascii_grid",
                "description": "Paint or patch the sprite using a 2D ASCII character grid and a character-to-hex-color legend.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "grid": {"type": "string", "description": "Multiline string where each character maps to legend ('.' is transparent)"},
                        "legend": {"type": "object", "description": "Mapping of single character to hex color e.g. {'#': '#000000', 'R': '#ff0000'}"},
                        "offset_x": {"type": "integer", "default": 0},
                        "offset_y": {"type": "integer", "default": 0},
                        "transparent_behavior": {"type": "string", "enum": ["clear", "skip"], "default": "clear"},
                    },
                    "required": ["grid", "legend"],
                },
            },
            {
                "name": "draw_shape",
                "description": "Deterministic geometric primitive drawing (line, rect, ellipse, flood_fill).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "shape": {"type": "string", "enum": ["line", "rect", "ellipse", "flood_fill"]},
                        "x0": {"type": "integer"},
                        "y0": {"type": "integer"},
                        "x1": {"type": "integer"},
                        "y1": {"type": "integer"},
                        "color": {"type": "string", "description": "Hex color e.g. '#3366cc'"},
                        "fill": {"type": "boolean", "default": True},
                    },
                    "required": ["shape", "x0", "y0", "color"],
                },
            },
            {
                "name": "auto_outline_and_shade",
                "description": "Deterministically generate a 1px outline and/or directional pixel-art shading.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "outline_color": {"type": "string", "default": "#000000"},
                        "outline_mode": {"type": "string", "enum": ["outside", "inside", "none"], "default": "outside"},
                        "apply_shading": {"type": "boolean", "default": False},
                        "light_dir": {"type": "string", "enum": ["top_left", "top_right", "top", "left", "right"], "default": "top_left"},
                    },
                },
            },
            {
                "name": "lint_and_repair",
                "description": "Run semantic review and optionally run deterministic repair rules on the sprite.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "auto_repair": {"type": "boolean", "default": True},
                    },
                },
            },
            {
                "name": "generate_color_ramp",
                "description": "Generate a hue-shifted pixel-art color ramp from shadow to highlight.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "base_color": {"type": "string"},
                        "steps": {"type": "integer", "default": 4},
                    },
                    "required": ["base_color"],
                },
            },
            {
                "name": "save_sprite",
                "description": "Save the active sprite document to disk.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string"},
                    },
                    "required": ["filepath"],
                },
            },
        ]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches a tool call by name and returns a structured JSON-serializable response."""
        if name == "init_workspace":
            filepath = arguments.get("filepath")
            if filepath:
                doc = Document()
                doc.load(filepath)
                self.workspace = SpriteWorkspace(
                    document=doc,
                    constraints={"required_size": doc.size, "must_have_transparent_background": True},
                )
            else:
                w = int(arguments.get("width", 16))
                h = int(arguments.get("height", 16))
                prompt = arguments.get("prompt", "")
                self.workspace = self.provider.construct_sprite(prompt=prompt, size=(w, h))
            return self.workspace.summary(include_grid=True)

        if name == "generate_color_ramp":
            from ..core.palette import PaletteOperations
            ramp = PaletteOperations.generate_color_ramp(
                arguments["base_color"],
                steps=int(arguments.get("steps", 4)),
            )
            return {"base_color": arguments["base_color"], "ramp": ramp}

        if self.workspace is None:
            self.workspace = self.provider.construct_sprite(prompt="default", size=(16, 16))

        wb = self.workspace.workbench

        if name == "inspect_sprite":
            include_grid = arguments.get("include_grid", True)
            return self.workspace.summary(include_grid=include_grid)

        elif name == "apply_ascii_grid":
            self.workspace.apply_ascii_grid(
                grid=arguments["grid"],
                legend=arguments["legend"],
                offset_x=int(arguments.get("offset_x", 0)),
                offset_y=int(arguments.get("offset_y", 0)),
                transparent_behavior=arguments.get("transparent_behavior", "clear"),
            )
            return self.workspace.summary(include_grid=True)

        elif name == "draw_shape":
            shape = arguments["shape"]
            x0 = int(arguments["x0"])
            y0 = int(arguments["y0"])
            color = arguments["color"]
            fill = bool(arguments.get("fill", True))
            if shape == "flood_fill":
                wb.flood_fill(x0, y0, color)
            elif shape == "line":
                wb.draw_line(x0, y0, int(arguments["x1"]), int(arguments["y1"]), color)
            elif shape == "rect":
                wb.draw_rect(x0, y0, int(arguments["x1"]), int(arguments["y1"]), color, fill=fill)
            elif shape == "ellipse":
                wb.draw_ellipse(x0, y0, int(arguments["x1"]), int(arguments["y1"]), color, fill=fill)
            else:
                raise ValueError(f"Unsupported shape: {shape}")
            self.workspace.refresh()
            return self.workspace.summary(include_grid=True)

        elif name == "auto_outline_and_shade":
            outline_mode = arguments.get("outline_mode", "outside")
            if outline_mode in ("outside", "inside"):
                wb.generate_outline(color=arguments.get("outline_color", "#000000"), mode=outline_mode)
            if arguments.get("apply_shading", False):
                wb.apply_shading(light_dir=arguments.get("light_dir", "top_left"))
            self.workspace.refresh()
            return self.workspace.summary(include_grid=True)

        elif name == "lint_and_repair":
            repair_report = None
            if arguments.get("auto_repair", True):
                repair_report = wb.repair()
            self.workspace.refresh()
            res = self.workspace.summary(include_grid=True)
            res["repair_report"] = repair_report
            return res

        elif name == "save_sprite":
            filepath = arguments["filepath"]
            wb.save(filepath)
            return {"saved": True, "filepath": filepath}

        raise ValueError(f"Unknown tool: {name}")
