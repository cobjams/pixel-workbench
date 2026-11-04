### Pixel Workbench (Reasoning Engine)

You are a professional Python developer with a talent for pixel art. You are skilled at building tools for autonomous, deterministic creation of art assets for games.

`pixel_workbench` is a standalone Python application and API that serves as a **Reasoning Engine** for pixel art. It is designed to be used equally well by humans and autonomous coding agents.

- **Semantic Focus:** The Workbench is not an "AI Image Generator". Its primary value is extracting structured, semantic metadata (`SpriteAnalysis`) from sprites so agents can reason about properties like `outline`, `clusters`, `symmetry`, and `lighting`.
- **Deterministic Editing:** Exposes high-level deterministic operations and a rule-based `repair` engine to fix common pixel art flaws safely.
- **Coding Agent Workspaces:** When working as an agent, use the `CodingAgentProvider` to initialize a `SpriteWorkspace`. This bundles the `Document`, `Analysis`, `Validation`, `Checkpoints`, and `History`, giving you a complete mental model of the sprite without needing to reverse engineer raw pixels.
- **Construction over Generation:** If you need to generate images, remember the philosophy is to *construct* sprites iteratively (`Inspect -> Plan -> Construct -> Validate -> Iterate -> Export`) rather than blindly hallucinating PNGs.

---

### Agent-Assisted Asset Development Workflow

1. **Inspect:**
   - Load an existing sprite or initialize a blank `SpriteWorkspace`.
   - Inspect semantic analysis (`palette`, `clusters`, `symmetry`, `semantic_regions`) and the lossless 2D ASCII representation (`workspace.to_ascii_grid()`).
2. **Plan:**
   - Snapshot a baseline before modifying the sprite using `workspace.checkpoint("before_edit")`.
   - Identify target semantic regions (`head`, `body`, `outline`, `shadow`, `highlight`) and set workspace `constraints` (e.g., `allowed_palette`, `max_colors`, `expected_outline_color`, `preserve_symmetry`).
3. **Construct:**
   - Use 2D ASCII grids (`workspace.apply_ascii_grid(grid, legend, preserve_whitespace=True, strict=True)`), geometric primitives (`draw_line`, `draw_rect`, `draw_ellipse`, `flood_fill`), deterministic outlining (`generate_outline`), hue-shifted ramps (`generate_color_ramp`), and directional shading (`apply_shading`).
   - `ApplyAsciiGrid` preserves leading/trailing spaces and blank rows when `List[str]` or space-based grids are provided, guaranteeing a lossless `Image -> ASCII Grid -> Image` round-trip invariant even on sprites with >100 colors or partial alpha.
4. **Validate (Pixel-Art Quality Assurance Suite):**
   - Run `workspace.regression_report("before_edit")` (or `analysis.regression.generate_regression_report`) to execute the 6-part Pixel-Art QA Suite:
     - `grid_roundtrip`: Verifies `Image -> ASCII Grid -> Image` produces 0 unintended pixel changes.
     - `palette_regression`: Verifies no unexpected colors were introduced and `max_colors` is respected.
     - `outline_regression`: Verifies no broken outlines or interior color leaks onto the boundary.
     - `symmetry_validation`: Verifies horizontal/vertical symmetry did not degrade below baseline.
     - `animation_regression`: Verifies frame dimensions, shared palette, center-of-mass stability, and pixel volume across animation frames (`check_animation_regression`).
     - `repair_regression`: Verifies repairs do not damage valid interior 1px details (eyes, highlights) or protected coordinates.
5. **Iterate & Safe Repair:**
   - Preview repairs safely with `workbench.repair(dry_run=True, safe=True)` to inspect proposed `modified_pixels` and `preserved_details` before mutating the image.
   - `RepairEngine(safe=True)` automatically preserves 1px interior details (eyes/highlights), horizontally symmetric detached particles (sparks/stars), repeated starfield motifs (`>= 3` pixels), and multi-pixel selective-outline (`sel-out`) accents, as well as any coordinates passed in `protect_coords`.
   - Use `workbench.undo()` at any time to roll back a command or repair.
6. **Export:**
   - Save the verified asset with `workbench.save(filepath)`.

---

### MCP Protocol Server (`pixel-workbench mcp-serve`)

- **Full `stdio` JSON-RPC 2.0 Server:** Run `pixel-workbench mcp-serve` (or `python3 -m pixel_workbench mcp-serve`) to start a spec-compliant MCP server over `stdio` supporting `initialize`, `notifications/initialized`, `ping`, `tools/list`, and `tools/call` (with both newline-delimited JSON-RPC and `Content-Length` framing).
- **Multimodal Tool Responses:** Passing `"include_preview_image": true` to `tools/call` returns an 8x nearest-neighbor upscaled PNG (`type: "image"`, `mimeType: "image/png"`) alongside the structured JSON text payload.
- **Programmatic Client:** Use `MCPStdioClient` in `pixel_workbench.tools.mcp_server` to spawn and test the MCP server over `stdio`.

---

### Future Priorities (Phase 5+)

- **Priority 5 (Multi-Layer Support):** Add named compositing layers (`base_body`, `armor`, `weapon`) to `Document` with non-destructive layer flattening on export.
- **Priority 6 (Animation Constraints):** Expand `Document.slice_frames` / `assemble_sprite_sheet` and `check_animation_regression` with onion-skin ASCII diffs and frame-to-frame anchor constraints.
