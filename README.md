# Pixel Workbench

**Pixel Workbench** is a deterministic **Semantic Reasoning and Construction Engine** for pixel art game assets, built for both autonomous coding agents and human developers.

Instead of relying on diffusion models that produce inconsistent pixel grids ("mixels"), noisy palettes, and broken outlines, Pixel Workbench gives coding agents a structured AST (`SpriteAnalysis`), a 2D ASCII grid interface, deterministic geometric primitives, and a rule-based pixel-art linter and repair engine.

---

## Core Capabilities

- **2D ASCII Grid Reader & Writer (`to_ascii_grid` / `apply_ascii_grid`):** Lets LLMs and coding agents read and paint entire sprites or sub-regions in a single step using a human- and token-friendly character grid + hex legend.
- **Deterministic Pixel-Art Primitives (`core/commands.py`):**
  - `DrawLine` (1px Bresenham line)
  - `DrawRect` & `DrawEllipse` (filled or 1px outlined)
  - `FloodFill` (4-way contiguous fill)
  - `GenerateOutline` (`outside` or `inside` 1px border around non-transparent pixels)
  - `ApplyShading` (directional top-left/top-right interior highlight & shadow pass)
  - `PaletteOperations.generate_color_ramp` (hue-shifted pixel art color ramps)
- **Semantic AST (`SpriteAnalysis`):** Extracts connected components, 1px outline coordinates, horizontal/vertical symmetry scores, bounding boxes, semantic regions (`head`, `body`, `shadow`, `highlight`, `outline`), and JSON-serializable summaries.
- **Rule-Based Linter & Repair (`RepairEngine`):**
  - `RemoveIsolatedPixelsRule`: Removes stray 1px noise.
  - `StandardizeOutlineColorRule`: Unifies inconsistent outline colors.
  - `NormalizePaletteRule`: Merges near-duplicate palette colors within a Euclidean RGB threshold.
  - `RemoveJaggiesRule`: Detects and removes 1px L-shaped staircase corner doubles on outlines.
  - Full `Document.history` integration so every command and repair action supports `undo()` and `redo()`.
- **Sprite Sheet Slicing & Assembly (`Document.slice_frames` / `assemble_sprite_sheet`):** Slice sprite sheets into individual frame `Document` objects and reassemble edited frames into horizontal strips or grids.
- **MCP / Agent Tool Server (`tools/mcp_server.py`):** Exposes 8 JSON-Schema tools (`init_workspace`, `inspect_sprite`, `apply_ascii_grid`, `draw_shape`, `auto_outline_and_shade`, `lint_and_repair`, `generate_color_ramp`, `save_sprite`) for immediate integration with autonomous coding agents.

---

## Quick Start

### Python Agent Workspace API

```python
from pixel_workbench.analysis.adapters.agent import CodingAgentProvider

provider = CodingAgentProvider()
ws = provider.construct_sprite(prompt="health potion", size=(8, 8))

# 1. Paint using a 2D ASCII grid
grid = """
...##...
...##...
..#RR#..
.#RhhR#.
.#RRRR#.
.#RssR#.
..####..
........
"""
legend = {
    "#": "#000000",
    "R": "#cc2233",
    "h": "#ff7788",
    "s": "#771122",
}
ws.apply_ascii_grid(grid, legend)

# 2. Inspect semantic analysis, validation diagnostics, and ASCII representation
summary = ws.summary(include_grid=True)
print(summary["analysis"]["palette_count"])  # 4
print(summary["validation"]["diagnostics"])
```

### CLI Usage

```bash
# Analyze a sprite and output JSON semantic metrics + ASCII grid
python3 -m pixel_workbench analyze path/to/sprite.png

# Output the 2D ASCII character grid and color legend
python3 -m pixel_workbench grid path/to/sprite.png

# Review a sprite for dimensions, transparency, stray pixels, and jaggies
python3 -m pixel_workbench review path/to/sprite.png

# Deterministically repair a sprite and save the result
python3 -m pixel_workbench repair path/to/sprite.png --output path/to/fixed.png

# Visual & JSON diff between two sprites
python3 -m pixel_workbench diff old.png new.png --image diff.png --json diff.json

# Export MCP tool schemas for coding agents
python3 -m pixel_workbench mcp-tools

# Invoke an MCP tool directly from the CLI
python3 -m pixel_workbench call-tool generate_color_ramp --args '{"base_color": "#3366cc", "steps": 4}'
```

---

## Development Progress & Roadmap

| Phase | Scope | Status |
| :--- | :--- | :--- |
| **Phase 1: Foundation** | Package configuration (`pyproject.toml`, `setup.py`), relative import cleanup, JSON serialization (`SpriteAnalysis.to_dict()`), alpha-preserving quantization, `RepairEngine` undo history integration, and wiring `ReasoningEngine.compare()`. | **Completed** |
| **Phase 2: Agent Ergonomics** | 2D ASCII grid serialization & application (`to_ascii_grid`, `apply_ascii_grid`), Bresenham `draw_line`, `draw_rect`, `draw_ellipse`, `flood_fill`, deterministic `generate_outline`, and directional `apply_shading`. | **Completed** |
| **Phase 3: Linting & Color Theory** | `RemoveJaggiesRule` (L-corner double detection & repair), `generate_color_ramp` with warm/cool hue-shifting, and enriched `review_sprite` diagnostics. | **Completed** |
| **Phase 4: MCP & Multi-Frame** | `AgentToolServer` (`tools/mcp_server.py`) with 8 agent tools, CLI subcommands (`repair`, `grid`, `mcp-tools`), and `Document.slice_frames` / `assemble_sprite_sheet`. | **Completed** |
| **Phase 5: Layers & Animation Constraints** | Named compositing layers (`Document.layers`), onion-skin frame diffing, and anti-banding / pillow-shading cluster analysis. | **Planned** |

---

## Running Tests

```bash
python3 -m unittest discover -s tests
```
