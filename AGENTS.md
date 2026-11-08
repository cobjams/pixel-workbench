# Pixel Workbench — Agent Instructions (`AGENTS.md`)

`pixel_workbench` is a standalone Python application, API, and Model Context Protocol (MCP) server that serves as a **Semantic Reasoning and Deterministic Construction Engine** for pixel art.

This file is divided into two sections depending on your role:
1. **[Section 1: For Tool-Using Agents (Creating & Editing Pixel Art)](#section-1-for-tool-using-agents-creating--editing-pixel-art)**
2. **[Section 2: For Tool-Making Agents (Developing & Extending Pixel Workbench)](#section-2-for-tool-making-agents-developing--extending-pixel-workbench)**

---

## Section 1: For Tool-Using Agents (Creating & Editing Pixel Art)

If the user is asking you to **create, inspect, modify, repair, or audit pixel-art sprites, icons, or sprite sheets**:

- **Load the Agent Skill:** Read [`.agents/skills/pixel-workbench/SKILL.md`](.agents/skills/pixel-workbench/SKILL.md) for step-by-step playbooks covering:
  1. Constructing new icons/sprites from scratch (`generate_color_ramp` $\rightarrow$ `init_workspace` $\rightarrow$ `apply_ascii_grid` / `draw_shape` $\rightarrow$ `auto_outline_and_shade`).
  2. Patching existing or indexed (`P`-mode) sprite sheets (`checkpoint_workspace` $\rightarrow$ localized `apply_ascii_grid` or `transform_sprite` $\rightarrow$ `regression_report`).
  3. Auditing and aligning multi-frame walk cycles (`inspect_animation` $\rightarrow$ `transform_sprite` with `shift_region`).
  4. Safe context-aware linting and repair (`lint_and_repair` with `dry_run=True, safe=True` and `undo_redo`).
- **Core Philosophy (Construction over Generation):** Never hallucinate raw PNG files blindly. Always follow the iterative 6-step loop:
  `Inspect -> Plan (Checkpoint) -> Construct / Transform -> Validate (6-Part QA Suite) -> Iterate / Repair -> Export`.
- **Multimodal Previews:** When calling MCP tools via `tools/call`, pass `"include_preview_image": true` to receive an 8× nearest-neighbor upscaled PNG preview alongside the structured JSON analysis.

---

## Section 2: For Tool-Making Agents (Developing & Extending Pixel Workbench)

If the user is asking you to **develop, debug, refactor, or add features to the `pixel_workbench` codebase**:

### 1. Architecture Overview

- **`core/` (`Document`, `Command`, `HistoryStack`, `PaletteOperations`):**
  - [`core/document.py`](core/document.py): Manages the PIL `Image`, file I/O, frame slicing/assembly (`slice_frames`, `assemble_sprite_sheet`), and undo/redo history stack.
  - [`core/commands.py`](core/commands.py): All pixel-mutating operations (`ApplyAsciiGrid`, `DrawLine`, `DrawRect`, `DrawEllipse`, `FloodFill`, `GenerateOutline`, `ApplyShading`, `Mirror`, `Crop`, `ResizeCanvas`, `ReplaceColor`, `ShiftRegion`, etc.).
- **`analysis/` (`SpriteWorkspace`, `SpriteAnalysis`, `RepairEngine`, `regression`):**
  - [`analysis/sprite_analysis.py`](analysis/sprite_analysis.py): Extracts structured semantic properties (`palette`, `connected_components`, `clusters`, `outline`, `symmetry`, `semantic_regions`) and lossless 2D ASCII grids (`to_ascii_grid`).
  - [`analysis/workspace.py`](analysis/workspace.py): `SpriteWorkspace` bundles `Document`, `Workbench`, `SpriteAnalysis`, named `checkpoints`, and `constraints`.
  - [`analysis/repair/`](analysis/repair/): Rule-based safe repair engine (`RemoveIsolatedPixelsRule`, `StandardizeOutlineColorRule`, `RemoveJaggiesRule`, `NormalizePaletteRule`).
  - [`analysis/regression.py`](analysis/regression.py): The 6-part Pixel-Art QA Suite (`check_grid_roundtrip`, `check_palette_regression`, `check_outline_regression`, `check_symmetry_validation`, `check_animation_regression`, `check_repair_regression`).
- **`tools/mcp_server.py` (`AgentToolServer`, `MCPStdioClient`):**
  - Zero-dependency MCP JSON-RPC 2.0 server over `stdio` (`pixel-workbench mcp-serve`) supporting both newline-delimited JSON-RPC and `Content-Length` framing.
- **`app.py` & `__main__.py` (`Workbench` & CLI):**
  - [`app.py`](app.py) is the canonical Python facade (`Workbench`). [`__main__.py`](__main__.py) exposes the CLI (`analyze`, `grid`, `repair`, `regression`, `diff`, `construct`, `mcp-serve`, `mcp-tools`, `call-tool`).

### 2. Contributor Rules & Invariants

1. **Zero External MCP Dependencies:** Keep `pixel_workbench` lightweight (`Pillow>=7.0.0` only). Do not introduce heavy external SDK requirements in `tools/mcp_server.py`.
2. **Command Pattern & Undoability:** Every new canvas or pixel mutation added to `Workbench` MUST be implemented as a `Command` subclass in [`core/commands.py`](core/commands.py) and executed via `Workbench._execute_command` so `undo()` and `redo()` work automatically.
3. **Preserve Indexed (`P`-mode) Compatibility:** Many game sprite sheets use indexed `'P'` mode with transparency metadata (`image.info["transparency"]`). New commands and analyses must handle both `'P'` and `'RGBA'` modes without corrupting the color table.
4. **Lossless ASCII Grid Round-Trip Invariant:** `Image -> to_ascii_grid() -> ApplyAsciiGrid -> Image` must always produce `0` unintended pixel changes (verified by `check_grid_roundtrip`), including sprites with >100 colors, partial alpha, blank rows, and leading/trailing spaces.
5. **Safe-by-Default Repairs:** Any new rule in `analysis/repair/` must respect `safe=True` and `protect_coords` so valid 1px interior details (eyes, specular highlights), symmetric particles, and selective-outline (`sel-out`) accents are never destroyed.
6. **Keep MCP & Skill Docs in Sync:** When adding or modifying an MCP tool in [`tools/mcp_server.py`](tools/mcp_server.py), include MCP `annotations` (`readOnlyHint`, `destructiveHint`, etc.) and update [`.agents/skills/pixel-workbench/SKILL.md`](.agents/skills/pixel-workbench/SKILL.md) and [`README.md`](README.md).

### 3. Testing Verification

Always run the full unit and integration test suite before committing changes:

```bash
python3 -m unittest discover -s tests -v
```

---

### 4. Roadmap Priorities (Phase 5+)

- **Multi-Layer Compositing:** Add named compositing layers (`base_body`, `armor`, `weapon`) to `Document` with non-destructive layer flattening on export.
- **Dedicated Frame-Slicing & Sheet-Assembly MCP Tools:** Expose `slice_frames` and `assemble_sprite_sheet` as standalone MCP workspace tools alongside `inspect_animation`.
- **Onion-Skin Animation Diffs:** Expand `inspect_animation` and `check_animation_regression` with frame-over-frame onion-skin ASCII diffs.
