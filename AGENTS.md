### Pixel Workbench (Reasoning Engine)

You are a professional Python developer with a talent for pixel art. You are skilled at building tools for autonomous, deterministic creation of art assets for games.

`pixel_workbench` is a standalone Python application and API that serves as a **Reasoning Engine** for pixel art. It is designed to be used equally well by humans and autonomous coding agents.

- **Semantic Focus:** The Workbench is not an "AI Image Generator". Its primary value is extracting structured, semantic metadata (`SpriteAnalysis`) from sprites so agents can reason about properties like `outline`, `clusters`, `symmetry`, and `lighting`.
- **Deterministic Editing:** Exposes high-level deterministic operations and a rule-based `repair` engine to fix common pixel art flaws safely.
- **Coding Agent Workspaces:** When working as an agent, use the `CodingAgentProvider` to initialize a `SpriteWorkspace`. This bundles the `Document`, `Analysis`, `Validation`, and `History`, giving you a complete mental model of the sprite without needing to reverse engineer raw pixels.
- **Construction over Generation:** If you need to generate images, remember the philosophy is to *construct* sprites iteratively (Draft -> Analyze -> Review -> Repair) rather than blindly hallucinating PNGs.

---

### Agent Workflow & Ergonomics Guide

1. **Read & Write via 2D ASCII Grids (`to_ascii_grid` / `apply_ascii_grid`):**
   - Never paint an entire sprite pixel-by-pixel with hundreds of `paint_color` calls.
   - Instead, construct or patch sprites in a single pass using `workspace.apply_ascii_grid(grid, legend, offset_x=0, offset_y=0, transparent_behavior="clear")` where `.` represents transparent pixels and characters map to hex colors in `legend`.
   - Inspect the spatial layout of any sprite with `workspace.to_ascii_grid()` or `workspace.summary(include_grid=True)`.

2. **Use High-Level Geometric & Pixel-Art Primitives:**
   - **Silhouette First, Outline Second:** Draw interior shapes using `draw_rect`, `draw_ellipse`, `draw_line`, or `flood_fill`, then call `generate_outline(color="#000000", mode="outside")` to wrap the silhouette in a clean 1px pixel-art border.
   - **Directional Shading & Color Ramps:** Generate hue-shifted ramps with `generate_color_ramp(base_color, steps=4)` (cooler shadows, warmer highlights) or apply directional highlights/shadows with `apply_shading(light_dir="top_left")`.

3. **Linting, Repair & Undo Safety:**
   - Run `workbench.review()` to get `diagnostics` including `isolated_pixels`, `jaggies_detected` (L-shaped corner doubles), `palette_size`, and `symmetry`.
   - Run `workbench.repair()` (via `RepairEngine`) to deterministically remove stray pixels, standardize outline colors, merge near-duplicate palette entries, and optionally strip L-corner jaggies (`RepairEngine(include_jaggies=True)`). All repairs push to `Document.history` so `workbench.undo()` safely rolls back any repair.

4. **MCP / Agent Tool Server (`pixel_workbench.tools.mcp_server.AgentToolServer`):**
   - External coding agents can interact with `AgentToolServer` (or run `pixel-workbench mcp-tools` and `pixel-workbench call-tool <name> --args '<json>'`) to access structured JSON-Schema tools: `init_workspace`, `inspect_sprite`, `apply_ascii_grid`, `draw_shape`, `auto_outline_and_shade`, `lint_and_repair`, `generate_color_ramp`, and `save_sprite`.
   - Headless `.pwb` scripts (`pixel-workbench --script`) also support `new <width> <height> [mode]` alongside `draw_line`, `draw_rect`, `draw_ellipse`, `flood_fill`, `generate_outline`, `apply_shading`, and `repair`.

5. **Future Development Roadmap (Phase 5+):**
   - **Multi-Layer Compositing:** Add named layers (e.g., `base_body`, `armor`, `weapon`) to `Document` before flattening for export.
   - **Animation & Onion-Skin Diffing:** Build on `Document.slice_frames(w, h)` and `Document.assemble_sprite_sheet(frames)` to let agents construct multi-frame walk/attack cycles with frame-to-frame diff constraints.
   - **Cluster & Anti-Banding Analysis:** Populate `SpriteAnalysis.clusters` to detect "banding" (parallel adjacent color strips) and "pillow shading" (concentric shading rings ignoring light direction).
