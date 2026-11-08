---
name: pixel-workbench
description: >-
  Deterministic pixel-art construction, semantic inspection, sprite-sheet editing,
  animation walk-cycle alignment, and 6-part QA regression testing using Pixel Workbench
  (via MCP tools or the Python API). Activate this skill whenever creating, modifying,
  auditing, or repairing pixel-art game assets, icons, or sprite sheets.
---

# Pixel Workbench — Agent Skill & Workflow Guide

Pixel Workbench is a deterministic reasoning, construction, and quality-assurance engine for pixel art. Always prefer **iterative, verifiable construction** (`Inspect -> Plan -> Construct -> Validate -> Iterate -> Export`) over unconstrained image generation.

---

## Core Principles

1. **Never Hallucinate Raw PNGs Blindly:** Construct or patch sprites using lossless 2D ASCII character grids (`apply_ascii_grid`), deterministic geometric primitives (`draw_shape`), and pixel-accurate transforms (`transform_sprite`).
2. **Always Checkpoint Before Editing:** Call `checkpoint_workspace` (or `workspace.checkpoint("before_edit")`) before mutating an existing asset so you can verify `changed_pixels` and QA invariants via `regression_report`.
3. **Respect Indexed (`P`-mode) Palettes:** When editing an existing `P`-mode sprite sheet, inspect its `palette` first and reuse existing hex colors (or palette indices) so the color table remains intact.
4. **Use Multimodal Previews When Available:** Pass `"include_preview_image": true` in MCP `tools/call` requests to inspect an 8× nearest-neighbor PNG preview alongside the structured JSON analysis.

---

## Playbook 1: Constructing a New Sprite Icon from Scratch

1. **Generate Color Ramp(s):**
   - Call `generate_color_ramp` (e.g., `{"base_color": "#dca124", "steps": 4}`) to create a hue-shifted ramp from dark shadow to specular highlight, plus choose a dark outline color (e.g., `#2a1d0c` or `#000000`).
2. **Initialize Workspace with QA Constraints:**
   - Call `init_workspace` with `width`, `height`, and `constraints`:
     ```json
     {
       "width": 16,
       "height": 16,
       "prompt": "golden key icon",
       "constraints": {
         "max_colors": 6,
         "expected_outline_color": "#2a1d0c",
         "disallow_new_jaggies": true
       }
     }
     ```
3. **Construct the Pixel Grid:**
   - Draft a 2D ASCII grid where `.` represents transparent pixels and single characters (`1`..`5`, `#`, etc.) map to hex colors in `legend`.
   - Call `apply_ascii_grid` with `strict=true` to verify uniform row widths and canvas bounds.
   - Alternatively, block out shapes with `draw_shape` (`rect`, `ellipse`, `line`, `flood_fill`) and call `auto_outline_and_shade` (`outline_mode="outside"`, `apply_shading=true`).
4. **Validate & Lint:**
   - Call `lint_and_repair` with `{"dry_run": true, "safe": true}` to check for stray pixels or broken outlines without damaging 1px interior highlights.
   - Call `regression_report` to verify `grid_roundtrip`, `palette_regression`, and `outline_regression`.
5. **Save:**
   - Call `save_sprite` with the target `filepath`.

---

## Playbook 2: Targeted Modification of an Existing Sprite Sheet

1. **Open & Snapshot:**
   - Call `init_workspace` with `{"filepath": "path/to/sheet.png"}`.
   - Call `checkpoint_workspace` with `{"name": "before_edit"}`.
2. **Inspect Palette & Coordinates:**
   - Review `analysis.palette` and `analysis.ascii_grid` from `inspect_sprite`.
   - If the sprite is a multi-frame sheet (e.g., 128×128 with 32×32 frames), identify the target frame's top-left offset `(offset_x, offset_y)`.
3. **Apply Localized Patch:**
   - For single pixels, call `transform_sprite` with `{"operation": "paint_pixel", "x": 16, "y": 16, "color": "#fff6cc"}`.
   - For multi-pixel patches, call `apply_ascii_grid` with `offset_x`, `offset_y`, and `transparent_behavior="skip"` so `.` leaves surrounding pixels untouched.
4. **Verify Zero Collateral Damage:**
   - Call `regression_report` with `{"checkpoint_name": "before_edit"}`.
   - Confirm `pixel_diff.changed_pixels` matches the exact number of pixels you intended to modify and `qa_suite.passed` is `true`.

---

## Playbook 3: Auditing & Aligning Multi-Frame Animations

1. **Inspect Animation Metrics:**
   - Call `inspect_animation` with `frame_width` and `frame_height` (and optional `row` for a specific walk-cycle strip):
     ```json
     {
       "frame_width": 32,
       "frame_height": 32,
       "row": 0,
       "anchor": "bottom_center",
       "max_anchor_shift": 1.0
     }
     ```
2. **Diagnose Lurching or Flickering Details:**
   - Compare `frame_bounding_boxes`, `centers_of_mass`, and `anchor_points` across frames.
   - If Frame 1 (`x = 32..64, y = 0..32`) is shifted 2px left relative to Frame 0, its bounding box and `bottom_center` anchor will be offset by `-2.0` on X.
3. **Shift Misaligned Frame Regions Safely:**
   - Call `transform_sprite` with `operation="shift_region"` bounded strictly to that frame's rectangle so adjacent frames are untouched:
     ```json
     {
       "operation": "shift_region",
       "dx": 2,
       "dy": 0,
       "left": 32,
       "upper": 0,
       "right": 64,
       "lower": 32
     }
     ```
4. **Re-Verify Animation QA:**
   - Re-run `inspect_animation` to confirm `passed: true` and consistent `anchor_points`.

---

## Playbook 4: Safe Context-Aware Repair & Undo

- **Preview First:** Always run `lint_and_repair` with `dry_run=true, safe=true` first to inspect `repair_report.actions` and `repair_report.preserved_details`.
- **Protect Custom Coordinates:** If a 1px asymmetric detail is intentional (e.g., a beauty mark or asymmetric wand tip), pass its coordinates in `protect_coords: [[x, y]]`.
- **Rollback Anytime:** Call `undo_redo` with `{"action": "undo"}` (or `{"action": "redo"}`) to step backward or forward through the command history stack.

---

## Quick Tool Reference

| MCP Tool | Purpose | Read-Only? |
| :--- | :--- | :---: |
| `init_workspace` | Create blank canvas or load PNG into a workspace session | No |
| `inspect_sprite` | Get `SpriteAnalysis`, validation diagnostics, and 2D ASCII grid | Yes |
| `apply_ascii_grid` | Paint/patch full canvas or sub-region from 2D ASCII grid | No |
| `draw_shape` | Draw deterministic `line`, `rect`, `ellipse`, or `flood_fill` | No |
| `transform_sprite` | `mirror`, `crop`, `resize_canvas`, `replace_color`, `paint_pixel`, `shift_region` | No |
| `auto_outline_and_shade` | Generate 1px `outside`/`inside` outline and directional shading | No |
| `lint_and_repair` | Run semantic review and safe/dry-run repair engine | Optional |
| `undo_redo` | Undo or redo the last editing command | No |
| `checkpoint_workspace` | Save named snapshot of the current sprite | No |
| `regression_report` | Run pixel diff and 6-part QA suite against checkpoint/file | Yes |
| `inspect_animation` | Slice sprite sheet frames and run animation QA checks | Yes |
| `generate_color_ramp` | Generate hue-shifted color ramp from shadow to highlight | Yes |
| `save_sprite` | Save active document to PNG (preserving `P` or `RGBA` mode) | No |
