# Pixel Workbench

**Pixel Workbench** is a deterministic **Semantic Reasoning, Construction, and Quality Assurance Engine** for pixel art game assets, built for autonomous coding agents and human developers.

Instead of relying on diffusion models that produce inconsistent pixel grids ("mixels"), noisy palettes, and broken outlines, Pixel Workbench gives coding agents a structured AST (`SpriteAnalysis`), a lossless 2D ASCII grid interface, deterministic geometric primitives, a context-aware pixel-art linter/repair engine, a visual regression QA test suite, and a full Model Context Protocol (`stdio` JSON-RPC 2.0) server.

---

## Agent-Assisted Asset Workflow

Pixel Workbench is designed around a deterministic six-step loop:
1. **Inspect:** Load a sprite into `SpriteWorkspace` and receive its semantic AST (`palette`, `clusters`, `symmetry`, `semantic_regions`) and lossless 2D ASCII representation.
2. **Plan:** Take a named snapshot (`workspace.checkpoint("baseline")`) and configure constraints (`allowed_palette`, `max_colors`, `expected_outline_color`, `preserve_symmetry`).
3. **Construct:** Paint or patch using 2D ASCII grids (`apply_ascii_grid`), geometric primitives (`draw_line`, `draw_rect`, `draw_ellipse`, `flood_fill`), deterministic outlining (`generate_outline`), hue-shifted color ramps (`generate_color_ramp`), and directional shading (`apply_shading`).
4. **Validate:** Run `workspace.regression_report("baseline")` to compare the modified sprite against the checkpoint and run the 6-part Pixel-Art QA Suite.
5. **Iterate:** Preview non-destructive repairs (`repair(dry_run=True, safe=True)`), apply safe repairs, or roll back via `undo()`.
6. **Export:** Save the verified PNG asset.

---

## Pixel-Art Quality Assurance Suite (`analysis/regression.py`)

Modeled after software regression testing, Pixel Workbench verifies six invariants on every edit:

| QA Check | Function | What It Verifies |
| :--- | :--- | :--- |
| **Grid Round-Trip** | `check_grid_roundtrip` | `Image → ASCII Grid → Image` produces 0 unintended pixel changes (including partial alpha, blank rows, leading/trailing spaces, and palettes >100 colors). |
| **Palette Regression** | `check_palette_regression` | No unauthorized colors introduced outside the baseline/allowed palette and `max_colors` is respected. |
| **Outline Regression** | `check_outline_regression` | No broken outlines or interior colors leaking onto a previously closed boundary. |
| **Symmetry Validation** | `check_symmetry_validation` | Intended horizontal/vertical symmetry is preserved and asymmetric pixel pairs are pinpointed. |
| **Animation Regression** | `check_animation_regression` | Frame dimensions, shared palette, center-of-mass shift, and opaque pixel volume remain consistent across frames. |
| **Repair Regression** | `check_repair_regression` | Safe repairs do not damage valid 1px interior details (eyes, specular highlights), protected coordinates, or selective-outline accents. |

---

## Safe, Context-Aware Repair Engine (`analysis/repair/`)

- **`RemoveIsolatedPixelsRule`:** Removes asymmetric stray 1px noise while automatically preserving:
  - 1px interior color clusters (eyes, highlights, buttons) surrounded by opaque pixels.
  - Horizontally symmetric 1px detached details (twin sparks, floating particles).
  - Starfield / particle motifs (`>= 3` detached pixels of identical color).
  - Explicitly protected coordinates (`protect_coords`).
- **`StandardizeOutlineColorRule`:** Fixes 1px rogue outline color errors and off-color brush noise while preserving:
  - Multi-pixel contiguous selective-outline (`sel-out`) accents (e.g., a golden crown rim or glowing tip).
  - Horizontally symmetric outline accents.
  - Borderless sprites where the interior fill naturally forms the outer boundary.
- **Dry-Run Mode (`dry_run=True`):** Returns proposed `modified_pixels` and `preserved_details` without mutating the document.

---

## MCP Server Integration (`tools/mcp_server.py`)

Pixel Workbench includes a complete, zero-dependency **MCP JSON-RPC 2.0 server over `stdio`** (`pixel-workbench mcp-serve`) compatible with Claude Code, Codex, Cursor, Antigravity, and any MCP client.

### MCP Configuration Example
```json
{
  "mcpServers": {
    "pixel-workbench": {
      "command": "python3",
      "args": ["-m", "pixel_workbench", "mcp-serve"]
    }
  }
}
```

### Exposed MCP Tools
- `init_workspace`: Initialize a new workspace or load an existing PNG with optional QA constraints.
- `inspect_sprite`: Retrieve semantic analysis, validation diagnostics, and the 2D ASCII grid.
- `apply_ascii_grid`: Paint/patch via 2D ASCII grid (`preserve_whitespace`, `strict` bounds checking).
- `draw_shape`: Draw deterministic `line`, `rect`, `ellipse`, or `flood_fill` primitives.
- `auto_outline_and_shade`: Deterministically generate 1px `outside`/`inside` outlines and directional shading.
- `lint_and_repair`: Run semantic review and safe/dry-run repairs with `protect_coords`.
- `checkpoint_workspace`: Save a named baseline snapshot for visual regression diffing.
- `regression_report`: Run the visual regression diff and QA test suite against a checkpoint or reference image.
- `generate_color_ramp`: Generate hue-shifted pixel art color ramps.
- `save_sprite`: Save the active sprite to disk.

*(Tip: Passing `"include_preview_image": true` in any `tools/call` request also returns an 8x nearest-neighbor upscaled PNG image in the MCP response content.)*

---

## CLI Usage

```bash
# Start the stdio MCP JSON-RPC 2.0 server
python3 -m pixel_workbench mcp-serve

# Analyze a sprite and output JSON semantic metrics + ASCII grid
python3 -m pixel_workbench analyze path/to/sprite.png

# Output the 2D ASCII character grid and color legend
python3 -m pixel_workbench grid path/to/sprite.png

# Preview proposed repairs without modifying the file (--dry-run)
python3 -m pixel_workbench repair path/to/sprite.png --dry-run

# Run a semantic visual regression & QA report between two sprites
python3 -m pixel_workbench regression before.png after.png

# Visual & JSON diff between two sprites
python3 -m pixel_workbench diff old.png new.png --image diff.png --json diff.json
```

---

## Development Roadmap

| Priority | Feature Area | Status |
| :--- | :--- | :--- |
| **Priority 1** | Fix ASCII grid round-trip edge cases (whitespace preservation, blank rows, >100 colors, strict mode) | **Completed** |
| **Priority 2** | Strengthen repair safety (`safe=True`, `dry_run=True`, `protect_coords`, sel-out & eye/spark preservation) | **Completed** |
| **Priority 3** | Complete MCP `stdio` JSON-RPC 2.0 transport (`mcp-serve`, `MCPStdioClient`, structured errors, image previews) | **Completed** |
| **Priority 4** | Semantic visual regression testing & 6-part Pixel-Art QA Suite (`analysis/regression.py`, checkpoints) | **Completed** |
| **Priority 5** | Multi-layer compositing support (`Document.layers`) | **Planned** |
| **Priority 6** | Advanced animation constraints & onion-skin diffing | **Planned** |

---

## Running Tests

```bash
python3 -m unittest discover -s tests
```
