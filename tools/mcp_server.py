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


class AgentToolServer:
    """
    Complete Model Context Protocol (MCP) JSON-RPC 2.0 server and tool dispatcher
    for autonomous coding agents working with Pixel Workbench.
    """
    SERVER_NAME = "pixel-workbench"
    SERVER_VERSION = "0.3.0"
    DEFAULT_PROTOCOL_VERSION = "2024-11-05"

    def __init__(self):
        self.provider = CodingAgentProvider()
        self.workspace: Optional[SpriteWorkspace] = None
        self.initialized: bool = False
        self.client_info: Dict[str, Any] = {}

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Returns the list of tool definitions in MCP JSON-Schema format."""
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
                        "x1": {"type": "integer", "description": "End X coordinate (required for line, rect, ellipse)"},
                        "y1": {"type": "integer", "description": "End Y coordinate (required for line, rect, ellipse)"},
                        "color": {"type": "string", "description": "Hex color e.g. '#3366cc'"},
                        "fill": {"type": "boolean", "default": True},
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
                        "dry_run": {"type": "boolean", "default": False, "description": "Propose repairs without mutating the image"},
                        "safe": {"type": "boolean", "default": True, "description": "Preserve symmetric details, particles, and multi-pixel outline accents"},
                        "include_jaggies": {"type": "boolean", "default": False},
                        "rule_names": {"type": "array", "items": {"type": "string"}},
                        "protect_coords": {
                            "type": "array",
                            "items": {"type": "array", "items": {"type": "integer"}},
                            "description": "List of [x, y] coordinates to protect from modification"
                        },
                    },
                },
            },
            {
                "name": "checkpoint_workspace",
                "description": "Save a named snapshot of the current sprite for subsequent visual regression comparison.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "default": "baseline"},
                    },
                },
            },
            {
                "name": "regression_report",
                "description": "Compare the current sprite against a checkpoint or reference file and run the pixel-art QA test suite.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "checkpoint_name": {"type": "string", "default": "initial"},
                        "reference_filepath": {"type": "string", "description": "Optional path to reference PNG"},
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

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Dispatches a tool call by name and returns a structured JSON-serializable response."""
        arguments = arguments or {}

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
            return self.workspace.summary(include_grid=True)

        if name == "generate_color_ramp":
            if "base_color" not in arguments:
                raise ValueError("Missing required argument: 'base_color'")
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
            if "grid" not in arguments or "legend" not in arguments:
                raise ValueError("Missing required arguments: 'grid' and 'legend'")
            self.workspace.apply_ascii_grid(
                grid=arguments["grid"],
                legend=arguments["legend"],
                offset_x=int(arguments.get("offset_x", 0)),
                offset_y=int(arguments.get("offset_y", 0)),
                transparent_behavior=arguments.get("transparent_behavior", "clear"),
                preserve_whitespace=arguments.get("preserve_whitespace"),
                strict=bool(arguments.get("strict", False)),
            )
            return self.workspace.summary(include_grid=True)

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
            self.workspace.refresh()
            res = self.workspace.summary(include_grid=True)
            res["repair_report"] = repair_report
            return res

        elif name == "checkpoint_workspace":
            cp_name = arguments.get("name", "baseline")
            self.workspace.checkpoint(cp_name)
            return {"checkpoint_saved": cp_name, "available_checkpoints": list(self.workspace.checkpoints.keys())}

        elif name == "regression_report":
            cp_name = arguments.get("checkpoint_name", "initial")
            ref_path = arguments.get("reference_filepath")
            return self.workspace.regression_report(checkpoint_name=cp_name, reference=ref_path)

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
                    },
                    "serverInfo": {
                        "name": self.SERVER_NAME,
                        "version": self.SERVER_VERSION,
                    },
                },
            }

        if method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

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
            tool_args = params.get("arguments") or {}
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
