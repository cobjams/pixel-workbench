import base64
import io
import json
import subprocess
import sys
from typing import Dict, Any, List, Optional, Tuple
from PIL import Image

from ..core.document import Document
from ..analysis.workspace import SpriteWorkspace
from ..analysis.adapters.agent import CodingAgentProvider
from ..analysis.regression import check_animation_regression


class AgentToolServer:
    """
    Complete Model Context Protocol (MCP) JSON-RPC 2.0 server and tool dispatcher
    for autonomous coding agents working with Pixel Workbench.
    """
    SERVER_NAME = "pixel-workbench"
    SERVER_VERSION = "0.3.0"
    DEFAULT_PROTOCOL_VERSION = "2024-11-05"

    SERVER_INSTRUCTIONS = (
        "Pixel Workbench is a deterministic reasoning, construction, and QA engine for pixel art.\n"
        "Follow the 6-step Agent-Assisted Asset Workflow:\n"
        "1. INSPECT: Call `init_workspace` (to create a canvas or open a PNG) or `inspect_sprite` to examine "
        "palette, clusters, outline, symmetry, semantic_regions, and the lossless 2D ASCII grid.\n"
        "2. PLAN: Call `checkpoint_workspace` before making edits and set QA constraints if needed.\n"
        "3. CONSTRUCT / MODIFY: Use `generate_color_ramp`, `apply_ascii_grid` (supports sub-region patching via "
        "offset_x/offset_y and transparent_behavior='skip'), `draw_shape`, `transform_sprite` "
        "(mirror, crop, resize_canvas, replace_color, paint_pixel, shift_region), or `auto_outline_and_shade`.\n"
        "4. VALIDATE: Call `regression_report` against your checkpoint to run the 6-part Pixel-Art QA Suite "
        "(grid_roundtrip, palette_regression, outline_regression, symmetry_validation, repair_regression), "
        "or call `inspect_animation` to validate multi-frame sprite sheets and walk cycles.\n"
        "5. ITERATE & REPAIR: Call `lint_and_repair` with `dry_run=true, safe=true` to preview fixes, or "
        "`undo_redo` to roll back changes.\n"
        "6. EXPORT: Call `save_sprite` to write the verified PNG (preserving P-mode indexed palettes or RGBA).\n"
        "Tip: Pass `\"include_preview_image\": true` in any `tools/call` request to receive an 8x nearest-neighbor "
        "PNG preview alongside the JSON payload."
    )

    def __init__(self):
        self.provider = CodingAgentProvider()
        self.workspaces: Dict[str, SpriteWorkspace] = {}
        self.active_workspace_id: str = "default"
        self.initialized: bool = False
        self.client_info: Dict[str, Any] = {}

    @property
    def workspace(self) -> Optional[SpriteWorkspace]:
        return self.workspaces.get(self.active_workspace_id)

    @workspace.setter
    def workspace(self, ws: Optional[SpriteWorkspace]) -> None:
        if ws is None:
            self.workspaces.pop(self.active_workspace_id, None)
        else:
            self.workspaces[self.active_workspace_id] = ws

    def _get_or_create_workspace(self, workspace_id: Optional[str] = None) -> SpriteWorkspace:
        ws_id = workspace_id or self.active_workspace_id or "default"
        self.active_workspace_id = ws_id
        if ws_id not in self.workspaces:
            self.workspaces[ws_id] = self.provider.construct_sprite(prompt="default", size=(16, 16))
        return self.workspaces[ws_id]

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Returns the list of tool definitions in MCP JSON-Schema format with MCP annotations."""
        return [
            {
                "name": "init_workspace",
                "description": "Initialize a new blank sprite workspace or open an existing PNG image file.",
                "annotations": {
                    "title": "Initialize Sprite Workspace",
                    "readOnlyHint": False,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "width": {"type": "integer", "default": 16},
                        "height": {"type": "integer", "default": 16},
                        "filepath": {"type": "string", "description": "Optional path to existing PNG"},
                        "prompt": {"type": "string", "default": ""},
                        "workspace_id": {"type": "string", "default": "default", "description": "Optional workspace session ID"},
                        "constraints": {
                            "type": "object",
                            "description": (
                                "Optional QA constraints (e.g. allowed_palette, max_colors, "
                                "expected_outline_color, preserve_symmetry, min_horizontal_symmetry, "
                                "min_vertical_symmetry, disallow_new_jaggies)"
                            ),
                        },
                    },
                },
            },
            {
                "name": "inspect_sprite",
                "description": "Returns the semantic analysis, validation report, and 2D ASCII character grid of the active sprite.",
                "annotations": {
                    "title": "Inspect Sprite & ASCII Grid",
                    "readOnlyHint": True,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "include_grid": {"type": "boolean", "default": True},
                        "workspace_id": {"type": "string", "description": "Optional workspace session ID"},
                    },
                },
            },
            {
                "name": "apply_ascii_grid",
                "description": "Paint or patch the sprite using a 2D ASCII character grid and a character-to-hex-color legend.",
                "annotations": {
                    "title": "Apply 2D ASCII Grid",
                    "readOnlyHint": False,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "grid": {
                            "oneOf": [
                                {"type": "string"},
                                {"type": "array", "items": {"type": "string"}}
                            ],
                            "description": "Multiline string or list of row strings where each character maps to legend ('.' is transparent)"
                        },
                        "legend": {"type": "object", "description": "Mapping of single character to hex color e.g. {'#': '#000000', 'R': '#ff0000'}"},
                        "offset_x": {"type": "integer", "default": 0},
                        "offset_y": {"type": "integer", "default": 0},
                        "transparent_behavior": {"type": "string", "enum": ["clear", "skip"], "default": "clear"},
                        "preserve_whitespace": {"type": "boolean", "description": "Preserve leading/trailing spaces and blank rows verbatim"},
                        "strict": {"type": "boolean", "default": False, "description": "Validate uniform row widths and canvas bounds"},
                        "workspace_id": {"type": "string", "description": "Optional workspace session ID"},
                    },
                    "required": ["grid", "legend"],
                },
            },
            {
                "name": "draw_shape",
                "description": "Deterministic geometric primitive drawing (line, rect, ellipse, flood_fill).",
                "annotations": {
                    "title": "Draw Geometric Primitive",
                    "readOnlyHint": False,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "shape": {"type": "string", "enum": ["line", "rect", "ellipse", "flood_fill"]},
                        "x0": {"type": "integer"},
                        "y0": {"type": "integer"},
                        "x1": {"type": "integer", "description": "End X coordinate (required for line, rect, ellipse)"},
                        "y1": {"type": "integer", "description": "End Y coordinate (required for line, rect, ellipse)"},
                        "color": {"type": "string", "description": "Hex color e.g. '#3366cc'"},
                        "fill": {"type": "boolean", "default": True},
                        "workspace_id": {"type": "string", "description": "Optional workspace session ID"},
                    },
                    "required": ["shape", "x0", "y0", "color"],
                    "allOf": [
                        {
                            "if": {
                                "properties": {"shape": {"enum": ["line", "rect", "ellipse"]}}
                            },
                            "then": {
                                "required": ["x1", "y1"]
                            },
                        }
                    ],
                },
            },
            {
                "name": "transform_sprite",
                "description": (
                    "Perform deterministic pixel or canvas transformations: mirror, crop, resize_canvas, "
                    "replace_color, paint_pixel, or shift_region (e.g. to align an animation frame)."
                ),
                "annotations": {
                    "title": "Transform Sprite or Region",
                    "readOnlyHint": False,
                    "destructiveHint": False,
                    "idempotentHint": False,
                    "openWorldHint": False,
                },
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["mirror", "crop", "resize_canvas", "replace_color", "paint_pixel", "shift_region"],
                        },
                        "direction": {"type": "string", "enum": ["horizontal", "vertical"], "default": "horizontal"},
                        "left": {"type": "integer", "description": "Left X bound (inclusive) for crop or shift_region"},
                        "upper": {"type": "integer", "description": "Upper Y bound (inclusive) for crop or shift_region"},
                        "right": {"type": "integer", "description": "Right X bound (exclusive) for crop or shift_region"},
                        "lower": {"type": "integer", "description": "Lower Y bound (exclusive) for crop or shift_region"},
                        "width": {"type": "integer", "description": "New canvas width for resize_canvas"},
                        "height": {"type": "integer", "description": "New canvas height for resize_canvas"},
                        "old_color": {"type": "string", "description": "Hex color to replace for replace_color"},
                        "new_color": {"type": "string", "description": "Replacement hex color for replace_color"},
                        "x": {"type": "integer", "description": "X coordinate for paint_pixel"},
                        "y": {"type": "integer", "description": "Y coordinate for paint_pixel"},
                        "color": {"type": "string", "description": "Hex color or palette index for paint_pixel"},
                        "dx": {"type": "integer", "default": 0, "description": "Horizontal pixel shift for shift_region"},
                        "dy": {"type": "integer", "default": 0, "description": "Vertical pixel shift for shift_region"},
                        "workspace_id": {"type": "string", "description": "Optional workspace session ID"},
                    },
                    "required": ["operation"],
                },
            },
            {
                "name": "auto_outline_and_shade",
                "description": "Deterministically generate a 1px outline and/or directional pixel-art shading.",
                "annotations": {
                    "title": "Auto Outline and Shade",
                    "readOnlyHint": False,
                    "destructiveHint": False,
                    "idempotentHint": False,
                    "openWorldHint": False,
                },
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "outline_color": {"type": "string", "default": "#000000"},
                        "outline_mode": {"type": "string", "enum": ["outside", "inside", "none"], "default": "outside"},
                        "apply_shading": {"type": "boolean", "default": False},
                        "light_dir": {"type": "string", "enum": ["top_left", "top_right", "top", "left", "right"], "default": "top_left"},
                        "workspace_id": {"type": "string", "description": "Optional workspace session ID"},
                    },
                },
            },
            {
                "name": "lint_and_repair",
                "description": "Run semantic review and optionally run deterministic repair rules on the sprite.",
                "annotations": {
                    "title": "Lint and Safe-Repair Sprite",
                    "readOnlyHint": False,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "auto_repair": {"type": "boolean", "default": True},
                        "dry_run": {"type": "boolean", "default": False, "description": "Propose repairs without mutating the image"},
                        "safe": {"type": "boolean", "default": True, "description": "Preserve symmetric details, particles, and multi-pixel outline accents"},
                        "include_jaggies": {"type": "boolean", "default": False},
                        "rule_names": {"type": "array", "items": {"type": "string"}},
                        "protect_coords": {
                            "type": "array",
                            "items": {"type": "array", "items": {"type": "integer"}},
                            "description": "List of [x, y] coordinates to protect from modification"
                        },
                        "workspace_id": {"type": "string", "description": "Optional workspace session ID"},
                    },
                },
            },
            {
                "name": "undo_redo",
                "description": "Undo or redo the most recent editing command in the workspace history stack.",
                "annotations": {
                    "title": "Undo / Redo Edit",
                    "readOnlyHint": False,
                    "destructiveHint": False,
                    "idempotentHint": False,
                    "openWorldHint": False,
                },
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["undo", "redo"], "default": "undo"},
                        "workspace_id": {"type": "string", "description": "Optional workspace session ID"},
                    },
                },
            },
            {
                "name": "checkpoint_workspace",
                "description": "Save a named snapshot of the current sprite for subsequent visual regression comparison.",
                "annotations": {
                    "title": "Save Workspace Checkpoint",
                    "readOnlyHint": False,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "default": "baseline"},
                        "workspace_id": {"type": "string", "description": "Optional workspace session ID"},
                    },
                },
            },
            {
                "name": "regression_report",
                "description": "Compare the current sprite against a checkpoint or reference file and run the pixel-art QA test suite.",
                "annotations": {
                    "title": "Run QA Regression Report",
                    "readOnlyHint": True,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "checkpoint_name": {"type": "string", "default": "initial"},
                        "reference_filepath": {"type": "string", "description": "Optional path to reference PNG"},
                        "workspace_id": {"type": "string", "description": "Optional workspace session ID"},
                    },
                },
            },
            {
                "name": "inspect_animation",
                "description": (
                    "Slice the active sprite sheet into animation frames of (frame_width x frame_height) "
                    "and run animation QA checks (bounding boxes, centers of mass, foot/anchor stability, palette drift)."
                ),
                "annotations": {
                    "title": "Inspect Sprite Sheet Animation",
                    "readOnlyHint": True,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "frame_width": {"type": "integer", "description": "Width of each animation frame in pixels"},
                        "frame_height": {"type": "integer", "description": "Height of each animation frame in pixels"},
                        "row": {"type": "integer", "description": "Optional 0-based row index to inspect a single animation strip"},
                        "frame_indices": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "description": "Optional subset of 0-based frame indices to evaluate",
                        },
                        "anchor": {
                            "type": "string",
                            "enum": ["bottom_center", "top_center", "center", "bottom_left", "bottom_right"],
                            "default": "bottom_center",
                        },
                        "max_com_shift": {"type": "number", "default": 4.0},
                        "max_anchor_shift": {"type": "number", "description": "Optional maximum allowed frame-to-frame anchor shift in pixels"},
                        "max_volume_delta_ratio": {"type": "number", "default": 0.35},
                        "include_frame_grids": {"type": "boolean", "default": False, "description": "Include 2D ASCII grids for each frame"},
                        "workspace_id": {"type": "string", "description": "Optional workspace session ID"},
                    },
                    "required": ["frame_width", "frame_height"],
                },
            },
            {
                "name": "generate_color_ramp",
                "description": "Generate a hue-shifted pixel-art color ramp from shadow to highlight.",
                "annotations": {
                    "title": "Generate Hue-Shifted Color Ramp",
                    "readOnlyHint": True,
                    "destructiveHint": False,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
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
                "annotations": {
                    "title": "Save Sprite to PNG",
                    "readOnlyHint": False,
                    "destructiveHint": True,
                    "idempotentHint": True,
                    "openWorldHint": False,
                },
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filepath": {"type": "string"},
                        "workspace_id": {"type": "string", "description": "Optional workspace session ID"},
                    },
                    "required": ["filepath"],
                },
            },
        ]

    def get_resource_list(self) -> List[Dict[str, Any]]:
        """Returns available MCP resources for the active workspace."""
        return [
            {
                "uri": "sprite://current/summary",
                "name": "Active Sprite Semantic Summary",
                "description": "Structured SpriteAnalysis, constraints, validation, and 2D ASCII grid of the active workspace.",
                "mimeType": "application/json",
            },
            {
                "uri": "sprite://current/grid",
                "name": "Active Sprite 2D ASCII Grid",
                "description": "Lossless 2D ASCII character grid and color legend for the active sprite.",
                "mimeType": "application/json",
            },
            {
                "uri": "sprite://current/preview.png",
                "name": "Active Sprite 8x Nearest-Neighbor Preview",
                "description": "Upscaled 8x PNG preview of the current canvas.",
                "mimeType": "image/png",
            },
        ]

    def read_resource(self, uri: str) -> List[Dict[str, Any]]:
        """Reads an MCP resource by URI."""
        ws = self._get_or_create_workspace()
        if uri == "sprite://current/summary":
            return [{
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(ws.summary(include_grid=True)),
            }]
        elif uri == "sprite://current/grid":
            return [{
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(ws.to_ascii_grid(include_legend=True)),
            }]
        elif uri == "sprite://current/preview.png":
            b64 = self._encode_preview_base64() or ""
            return [{
                "uri": uri,
                "mimeType": "image/png",
                "blob": b64,
            }]
        raise ValueError(f"Unknown resource URI: {uri}")

    def get_prompt_list(self) -> List[Dict[str, Any]]:
        """Returns reusable MCP prompt templates for common pixel-art workflows."""
        return [
            {
                "name": "construct-sprite",
                "description": "Step-by-step workflow to construct a new pixel-art icon or character sprite from scratch.",
                "arguments": [
                    {"name": "subject", "description": "What sprite to construct (e.g. '16x16 golden key')", "required": True},
                    {"name": "size", "description": "Canvas dimensions e.g. '16x16' or '32x32'", "required": False},
                ],
            },
            {
                "name": "edit-sprite-sheet",
                "description": "Workflow for making localized pixel edits to an existing sprite or indexed P-mode sprite sheet.",
                "arguments": [
                    {"name": "filepath", "description": "Path to the PNG sprite or sprite sheet", "required": True},
                    {"name": "goal", "description": "Description of the desired edit", "required": True},
                ],
            },
            {
                "name": "audit-animation",
                "description": "Workflow for diagnosing and fixing frame alignment or detail drift across a walk cycle or animation strip.",
                "arguments": [
                    {"name": "filepath", "description": "Path to the sprite sheet PNG", "required": True},
                    {"name": "frame_size", "description": "Frame dimensions e.g. '32x32'", "required": True},
                ],
            },
        ]

    def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        arguments = arguments or {}
        if name == "construct-sprite":
            subject = arguments.get("subject", "16x16 pixel art icon")
            size = arguments.get("size", "16x16")
            return {
                "description": f"Construct {subject} ({size})",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"Construct a deterministic pixel-art sprite for '{subject}' at size {size}:\n"
                                "1. Call `generate_color_ramp` to create a cohesive hue-shifted ramp.\n"
                                "2. Call `init_workspace` with the target dimensions and QA constraints.\n"
                                "3. Construct the silhouette and interior details using `apply_ascii_grid` (with `strict=true`) "
                                "or `draw_shape` + `auto_outline_and_shade`.\n"
                                "4. Call `regression_report` and `lint_and_repair` (`dry_run=true, safe=true`) to verify quality.\n"
                                "5. Save the result with `save_sprite`."
                            ),
                        },
                    }
                ],
            }
        elif name == "edit-sprite-sheet":
            filepath = arguments.get("filepath", "sprite.png")
            goal = arguments.get("goal", "modify details")
            return {
                "description": f"Edit {filepath}: {goal}",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"Modify '{filepath}' to achieve: {goal}\n"
                                "1. Call `init_workspace` with `filepath` and immediately call `checkpoint_workspace` (`name='before_edit'`).\n"
                                "2. Inspect the palette and ASCII grid via `inspect_sprite`. If the image is indexed (`P` mode), reuse existing palette colors.\n"
                                "3. Apply localized changes using `apply_ascii_grid` (with `offset_x`, `offset_y`, `transparent_behavior='skip'`) or `transform_sprite`.\n"
                                "4. Run `regression_report` against `'before_edit'` to confirm only intended pixels changed and no palette/outline regressions occurred."
                            ),
                        },
                    }
                ],
            }
        elif name == "audit-animation":
            filepath = arguments.get("filepath", "sheet.png")
            frame_size = arguments.get("frame_size", "32x32")
            return {
                "description": f"Audit animation in {filepath} ({frame_size})",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                f"Audit and stabilize the animation frames in '{filepath}' (frame size {frame_size}):\n"
                                "1. Open the sheet with `init_workspace` and save a `checkpoint_workspace`.\n"
                                "2. Call `inspect_animation` with `frame_width` and `frame_height` to inspect `frame_bounding_boxes`, "
                                "`centers_of_mass`, and `anchor_points`.\n"
                                "3. If any frames drift off-axis, use `transform_sprite` (`operation='shift_region'`) bounded to that frame's "
                                "`left, upper, right, lower` rectangle to align it without affecting adjacent frames.\n"
                                "4. Re-run `inspect_animation` and `regression_report` to verify alignment."
                            ),
                        },
                    }
                ],
            }
        raise ValueError(f"Unknown prompt: {name}")

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Dispatches a tool call by name and returns a structured JSON-serializable response."""
        arguments = dict(arguments or {})
        ws_id = arguments.get("workspace_id")
        if ws_id:
            self.active_workspace_id = str(ws_id)

        if name == "init_workspace":
            filepath = arguments.get("filepath")
            custom_constraints = arguments.get("constraints")
            if filepath:
                doc = Document()
                doc.load(filepath)
                constraints = {"required_size": doc.size, "must_have_transparent_background": True}
                if custom_constraints:
                    constraints.update(custom_constraints)
                self.workspace = SpriteWorkspace(document=doc, constraints=constraints)
            else:
                w = int(arguments.get("width", 16))
                h = int(arguments.get("height", 16))
                if w <= 0 or h <= 0:
                    raise ValueError(f"Invalid workspace dimensions: ({w}, {h}). Width and height must be positive.")
                prompt = arguments.get("prompt", "")
                self.workspace = self.provider.construct_sprite(
                    prompt=prompt,
                    size=(w, h),
                    constraints=custom_constraints,
                )
            res = self.workspace.summary(include_grid=True)
            res["workspace_id"] = self.active_workspace_id
            return res

        if name == "generate_color_ramp":
            if "base_color" not in arguments:
                raise ValueError("Missing required argument: 'base_color'")
            from ..core.palette import PaletteOperations
            ramp = PaletteOperations.generate_color_ramp(
                arguments["base_color"],
                steps=int(arguments.get("steps", 4)),
            )
            return {"base_color": arguments["base_color"], "ramp": ramp}

        ws = self._get_or_create_workspace(ws_id)
        wb = ws.workbench

        if name == "inspect_sprite":
            include_grid = arguments.get("include_grid", True)
            return ws.summary(include_grid=include_grid)

        elif name == "apply_ascii_grid":
            if "grid" not in arguments or "legend" not in arguments:
                raise ValueError("Missing required arguments: 'grid' and 'legend'")
            ws.apply_ascii_grid(
                grid=arguments["grid"],
                legend=arguments["legend"],
                offset_x=int(arguments.get("offset_x", 0)),
                offset_y=int(arguments.get("offset_y", 0)),
                transparent_behavior=arguments.get("transparent_behavior", "clear"),
                preserve_whitespace=arguments.get("preserve_whitespace"),
                strict=bool(arguments.get("strict", False)),
            )
            return ws.summary(include_grid=True)

        elif name == "draw_shape":
            for req in ("shape", "x0", "y0", "color"):
                if req not in arguments or arguments[req] is None:
                    raise ValueError(f"Missing required argument for draw_shape: '{req}'")
            shape = arguments["shape"]
            if shape not in ("flood_fill", "line", "rect", "ellipse"):
                raise ValueError(f"Unsupported shape: {shape}")
            if shape in ("line", "rect", "ellipse"):
                for req in ("x1", "y1"):
                    if req not in arguments or arguments[req] is None:
                        raise ValueError(
                            f"Missing required argument for draw_shape (shape='{shape}'): '{req}'"
                        )
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
            ws.refresh()
            return ws.summary(include_grid=True)

        elif name == "transform_sprite":
            op = arguments.get("operation")
            if not op:
                raise ValueError("Missing required argument for transform_sprite: 'operation'")
            if op == "mirror":
                direction = arguments.get("direction", "horizontal")
                wb.mirror(direction=direction)
            elif op == "crop":
                for req in ("left", "upper", "right", "lower"):
                    if req not in arguments or arguments[req] is None:
                        raise ValueError(f"Missing required argument for transform_sprite (crop): '{req}'")
                wb.crop(int(arguments["left"]), int(arguments["upper"]), int(arguments["right"]), int(arguments["lower"]))
            elif op == "resize_canvas":
                for req in ("width", "height"):
                    if req not in arguments or arguments[req] is None:
                        raise ValueError(f"Missing required argument for transform_sprite (resize_canvas): '{req}'")
                wb.resize_canvas(int(arguments["width"]), int(arguments["height"]))
            elif op == "replace_color":
                for req in ("old_color", "new_color"):
                    if req not in arguments or arguments[req] is None:
                        raise ValueError(f"Missing required argument for transform_sprite (replace_color): '{req}'")
                wb.replace_color(arguments["old_color"], arguments["new_color"])
            elif op == "paint_pixel":
                for req in ("x", "y", "color"):
                    if req not in arguments or arguments[req] is None:
                        raise ValueError(f"Missing required argument for transform_sprite (paint_pixel): '{req}'")
                x, y, col = int(arguments["x"]), int(arguments["y"]), arguments["color"]
                if ws.document.mode == "P":
                    from ..core.commands import parse_color_value
                    idx = parse_color_value(col, "P", document=ws.document)
                    wb.paint_index(x, y, idx)
                else:
                    wb.paint_color(x, y, col)
            elif op == "shift_region":
                dx = int(arguments.get("dx", 0))
                dy = int(arguments.get("dy", 0))
                wb.shift_region(
                    dx=dx,
                    dy=dy,
                    left=arguments.get("left"),
                    upper=arguments.get("upper"),
                    right=arguments.get("right"),
                    lower=arguments.get("lower"),
                )
            else:
                raise ValueError(f"Unsupported transform_sprite operation: {op}")
            ws.refresh()
            return ws.summary(include_grid=True)

        elif name == "auto_outline_and_shade":
            outline_mode = arguments.get("outline_mode", "outside")
            if outline_mode in ("outside", "inside"):
                wb.generate_outline(color=arguments.get("outline_color", "#000000"), mode=outline_mode)
            if arguments.get("apply_shading", False):
                wb.apply_shading(light_dir=arguments.get("light_dir", "top_left"))
            ws.refresh()
            return ws.summary(include_grid=True)

        elif name == "lint_and_repair":
            repair_report = None
            protect_raw = arguments.get("protect_coords")
            protect_set = {(int(pt[0]), int(pt[1])) for pt in protect_raw} if protect_raw else None
            if arguments.get("auto_repair", True):
                repair_report = wb.repair(
                    dry_run=bool(arguments.get("dry_run", False)),
                    safe=bool(arguments.get("safe", True)),
                    include_jaggies=bool(arguments.get("include_jaggies", False)),
                    rule_names=arguments.get("rule_names"),
                    protect_coords=protect_set,
                )
            ws.refresh()
            res = ws.summary(include_grid=True)
            res["repair_report"] = repair_report
            return res

        elif name == "undo_redo":
            action = arguments.get("action", "undo")
            if action == "undo":
                applied = wb.undo()
            elif action == "redo":
                applied = wb.redo()
            else:
                raise ValueError(f"Invalid undo_redo action: '{action}'. Expected 'undo' or 'redo'.")
            ws.refresh()
            res = ws.summary(include_grid=True)
            res["action"] = action
            res["applied"] = bool(applied)
            return res

        elif name == "checkpoint_workspace":
            cp_name = arguments.get("name", "baseline")
            ws.checkpoint(cp_name)
            return {"checkpoint_saved": cp_name, "available_checkpoints": list(ws.checkpoints.keys())}

        elif name == "regression_report":
            cp_name = arguments.get("checkpoint_name", "initial")
            ref_path = arguments.get("reference_filepath")
            return ws.regression_report(checkpoint_name=cp_name, reference=ref_path)

        elif name == "inspect_animation":
            for req in ("frame_width", "frame_height"):
                if req not in arguments or arguments[req] is None:
                    raise ValueError(f"Missing required argument for inspect_animation: '{req}'")
            fw = int(arguments["frame_width"])
            fh = int(arguments["frame_height"])
            if fw <= 0 or fh <= 0:
                raise ValueError("frame_width and frame_height must be positive integers.")
            all_frames = ws.document.slice_frames(fw, fh)
            if not all_frames:
                raise ValueError(
                    f"No frames of size ({fw}, {fh}) could be sliced from canvas of size {ws.document.size}."
                )
            cols = max(1, ws.document.width // fw)
            selected_frames = all_frames
            if "row" in arguments and arguments["row"] is not None:
                r = int(arguments["row"])
                start = r * cols
                selected_frames = all_frames[start : start + cols]
            elif "frame_indices" in arguments and arguments["frame_indices"] is not None:
                selected_frames = [all_frames[int(i)] for i in arguments["frame_indices"] if 0 <= int(i) < len(all_frames)]

            report = check_animation_regression(
                selected_frames,
                max_com_shift=float(arguments.get("max_com_shift", 4.0)),
                max_volume_delta_ratio=float(arguments.get("max_volume_delta_ratio", 0.35)),
                anchor=arguments.get("anchor", "bottom_center"),
                max_anchor_shift=float(arguments["max_anchor_shift"]) if arguments.get("max_anchor_shift") is not None else None,
            )
            report["frame_size"] = [fw, fh]
            report["sheet_columns"] = cols
            report["total_sheet_frames"] = len(all_frames)
            if arguments.get("include_frame_grids", False):
                from ..analysis.sprite_analysis import SpriteAnalysis
                report["frame_grids"] = [
                    SpriteAnalysis(f.image.convert("RGBA")).to_ascii_grid(include_legend=True)
                    for f in selected_frames
                ]
            return report

        elif name == "save_sprite":
            if "filepath" not in arguments:
                raise ValueError("Missing required argument: 'filepath'")
            filepath = arguments["filepath"]
            wb.save(filepath)
            return {"saved": True, "filepath": filepath}

        raise ValueError(f"Unknown tool: {name}")

    def _encode_preview_base64(self, zoom: int = 8) -> Optional[str]:
        if not self.workspace or not self.workspace.document.image:
            return None
        img = self.workspace.document.image.convert("RGBA")
        scaled = img.resize((img.width * zoom, img.height * zoom), resample=Image.NEAREST)
        buf = io.BytesIO()
        scaled.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("ascii")

    # -------------------------------------------------------------------------
    # MCP JSON-RPC 2.0 Transport Layer
    # -------------------------------------------------------------------------

    def handle_rpc_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Processes a single JSON-RPC 2.0 request or notification dictionary.
        Returns a JSON-RPC 2.0 response dictionary for requests, or None for notifications.
        """
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return {
                "jsonrpc": "2.0",
                "id": message.get("id") if isinstance(message, dict) else None,
                "error": {"code": -32600, "message": "Invalid Request: expected jsonrpc '2.0'."},
            }

        method = message.get("method")
        msg_id = message.get("id")
        params = message.get("params") or {}

        # Notifications do not have an 'id' field and must not receive a response
        is_notification = "id" not in message

        if method == "notifications/initialized" or method == "initialized":
            self.initialized = True
            return None if is_notification else {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        if is_notification:
            return None

        if method == "initialize":
            req_version = params.get("protocolVersion", self.DEFAULT_PROTOCOL_VERSION)
            self.client_info = params.get("clientInfo", {})
            self.initialized = True
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": req_version,
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                        "prompts": {"listChanged": False},
                    },
                    "serverInfo": {
                        "name": self.SERVER_NAME,
                        "version": self.SERVER_VERSION,
                    },
                    "instructions": self.SERVER_INSTRUCTIONS,
                },
            }

        if method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        if method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "resources": self.get_resource_list(),
                },
            }

        if method == "resources/read":
            uri = params.get("uri")
            if not uri:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": "Invalid params: 'uri' is required for resources/read."},
                }
            try:
                contents = self.read_resource(uri)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"contents": contents},
                }
            except Exception as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": str(exc)},
                }

        if method == "prompts/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "prompts": self.get_prompt_list(),
                },
            }

        if method == "prompts/get":
            prompt_name = params.get("name")
            prompt_args = params.get("arguments") or {}
            if not prompt_name:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": "Invalid params: 'name' is required for prompts/get."},
                }
            try:
                prompt_res = self.get_prompt(prompt_name, prompt_args)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": prompt_res,
                }
            except Exception as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": str(exc)},
                }

        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "tools": self.get_tool_schemas(),
                },
            }

        if method == "tools/call":
            tool_name = params.get("name")
            tool_args = dict(params.get("arguments") or {})
            include_image = bool(params.get("include_preview_image", False) or tool_args.pop("include_preview_image", False))

            if not tool_name or not isinstance(tool_name, str):
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32602, "message": "Invalid params: 'name' is required for tools/call."},
                }

            known_names = {t["name"] for t in self.get_tool_schemas()}
            if tool_name not in known_names:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({
                                    "error": f"Unknown tool: {tool_name}",
                                    "error_type": "UnknownToolError",
                                    "available_tools": sorted(known_names),
                                }),
                            }
                        ],
                        "isError": True,
                    },
                }

            try:
                output = self.call_tool(tool_name, tool_args)
                content_items: List[Dict[str, Any]] = [
                    {"type": "text", "text": json.dumps(output)}
                ]
                if include_image:
                    b64_png = self._encode_preview_base64()
                    if b64_png:
                        content_items.append({
                            "type": "image",
                            "data": b64_png,
                            "mimeType": "image/png",
                        })
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": content_items,
                        "isError": False,
                    },
                }
            except Exception as exc:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({
                                    "error": str(exc),
                                    "error_type": type(exc).__name__,
                                    "tool": tool_name,
                                }),
                            }
                        ],
                        "isError": True,
                    },
                }

        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        }

    def serve_stdio(self, in_stream=None, out_stream=None) -> None:
        """
        Runs the MCP JSON-RPC 2.0 server loop over stdio (newline-delimited JSON-RPC).
        """
        in_stream = in_stream or sys.stdin
        out_stream = out_stream or sys.stdout

        while True:
            line = in_stream.readline()
            if not line:
                break
            stripped = line.strip()
            if not stripped:
                continue

            # Support optional Content-Length header framing if sent by an LSP-style client
            if stripped.lower().startswith("content-length:"):
                length = int(stripped.split(":", 1)[1].strip())
                # Consume blank header separator line
                in_stream.readline()
                body = in_stream.read(length)
                raw_json = body
                use_content_length = True
            else:
                raw_json = stripped
                use_content_length = False

            try:
                msg = json.loads(raw_json)
            except json.JSONDecodeError as exc:
                resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {exc}"},
                }
            else:
                resp = self.handle_rpc_message(msg)

            if resp is not None:
                payload = json.dumps(resp)
                if use_content_length:
                    out_stream.write(f"Content-Length: {len(payload.encode('utf-8'))}\r\n\r\n{payload}")
                else:
                    out_stream.write(payload + "\n")
                out_stream.flush()


class MCPStdioClient:
    """
    Lightweight MCP client over stdio for integration testing and programmatic agent orchestration.
    """
    def __init__(self, command: Optional[List[str]] = None):
        self.command = command or [sys.executable, "-m", "pixel_workbench", "mcp-serve"]
        self.proc: Optional[subprocess.Popen] = None
        self._next_id = 1

    def __enter__(self) -> "MCPStdioClient":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def start(self) -> None:
        self.proc = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

    def close(self) -> None:
        if self.proc:
            for stream in (self.proc.stdin, self.proc.stdout, self.proc.stderr):
                if stream:
                    try:
                        stream.close()
                    except Exception:
                        pass
            try:
                self.proc.wait(timeout=3)
            except Exception:
                self.proc.kill()
            self.proc = None

    def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.proc or not self.proc.stdin or not self.proc.stdout:
            raise RuntimeError("MCPStdioClient subprocess is not running.")
        req_id = self._next_id
        self._next_id += 1
        req = {"jsonrpc": "2.0", "id": req_id, "method": method}
        if params is not None:
            req["params"] = params
        self.proc.stdin.write(json.dumps(req) + "\n")
        self.proc.stdin.flush()

        resp_line = self.proc.stdout.readline()
        if not resp_line:
            stderr_out = self.proc.stderr.read() if self.proc.stderr else ""
            raise RuntimeError(f"MCP server closed stream unexpectedly. stderr: {stderr_out}")
        return json.loads(resp_line)

    def send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        if not self.proc or not self.proc.stdin:
            raise RuntimeError("MCPStdioClient subprocess is not running.")
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()

    def initialize(self) -> Dict[str, Any]:
        resp = self.send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "pixel-workbench-test-client", "version": "1.0.0"},
            },
        )
        self.send_notification("notifications/initialized")
        return resp["result"]

    def list_tools(self) -> List[Dict[str, Any]]:
        resp = self.send_request("tools/list")
        return resp["result"]["tools"]

    def list_resources(self) -> List[Dict[str, Any]]:
        resp = self.send_request("resources/list")
        return resp["result"]["resources"]

    def read_resource(self, uri: str) -> List[Dict[str, Any]]:
        resp = self.send_request("resources/read", {"uri": uri})
        return resp["result"]["contents"]

    def list_prompts(self) -> List[Dict[str, Any]]:
        resp = self.send_request("prompts/list")
        return resp["result"]["prompts"]

    def get_prompt(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        resp = self.send_request("prompts/get", {"name": name, "arguments": arguments or {}})
        return resp["result"]

    def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
        include_preview_image: bool = False
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {"name": name, "arguments": arguments or {}}
        if include_preview_image:
            params["include_preview_image"] = True
        resp = self.send_request("tools/call", params)
        if "error" in resp:
            return {"isError": True, "rpc_error": resp["error"]}
        result = resp["result"]
        text_items = [c["text"] for c in result.get("content", []) if c.get("type") == "text"]
        parsed_data = json.loads(text_items[0]) if text_items else {}
        return {
            "isError": result.get("isError", False),
            "data": parsed_data,
            "raw_content": result.get("content", []),
        }
