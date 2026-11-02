### Pixel Workbench (Reasoning Engine)

`pixel_workbench` is a standalone Python application and API that serves as a **Reasoning Engine** for pixel art. It is designed to be used equally well by humans and autonomous coding agents.

- **Semantic Focus:** The Workbench is not an "AI Image Generator". Its primary value is extracting structured, semantic metadata (`SpriteAnalysis`) from sprites so agents can reason about properties like `outline`, `clusters`, `symmetry`, and `lighting`.
- **Deterministic Editing:** Exposes high-level deterministic operations and a rule-based `repair` engine to fix common pixel art flaws safely.
- **Coding Agent Workspaces:** When working as an agent, use the `CodingAgentProvider` to initialize a `SpriteWorkspace`. This bundles the `Document`, `Analysis`, `Validation`, and `History`, giving you a complete mental model of the sprite without needing to reverse engineer raw pixels.
- **Construction over Generation:** If you need to generate images, remember the philosophy is to *construct* sprites iteratively (Draft -> Analyze -> Review -> Repair) rather than blindly hallucinating PNGs.
