from .core.document import Document
from .core.commands import (
    PaintIndex,
    PaintColor,
    ReplaceIndex,
    ReplaceColor,
    Mirror,
    Crop,
    ResizeCanvas,
    DrawLine,
    DrawRect,
    DrawEllipse,
    FloodFill,
    GenerateOutline,
    ApplyAsciiGrid,
    ApplyShading,
)
from .core.palette import PaletteOperations

class Workbench:
    """
    Canonical Python API for Pixel Workbench.
    Used by agents, CLI, and GUI.
    """
    def __init__(self):
        self.document = Document()

        # Lazy load ReasoningEngine to avoid circular dependencies if any
        from .analysis.engine import ReasoningEngine
        self.engine = ReasoningEngine()

    def open(self, filepath):
        """Loads an image into the document."""
        self.document.load(filepath)

    def open_document(self, document: Document):
        """Replaces the active document with a given one."""
        self.document = document

    def save(self, filepath=None):
        """Saves the current document to a file."""
        self.document.save(filepath)

    def _execute_command(self, command, name):
        """Executes a command and pushes state to history."""
        # Push state BEFORE executing the command so we can undo it
        self.document.push_state(name)
        try:
            command.execute(self.document)
        except Exception as e:
            # If command fails, pop the state we just pushed to rollback
            self.undo()
            raise e

    def paint_index(self, x, y, index):
        """Paints a single pixel with a palette index ('P' mode only)."""
        cmd = PaintIndex(x, y, index)
        self._execute_command(cmd, f"paint_index {x} {y} {index}")

    def paint_color(self, x, y, color):
        """Paints a single pixel with a hex color or RGB(A) tuple."""
        cmd = PaintColor(x, y, color)
        self._execute_command(cmd, f"paint_color {x} {y} {color}")

    def replace_index(self, old_index, new_index):
        """Replaces all occurrences of an old index with a new index ('P' mode only)."""
        cmd = ReplaceIndex(old_index, new_index)
        self._execute_command(cmd, f"replace_index {old_index} {new_index}")

    def replace_color(self, old_color, new_color):
        """
        Replaces a color (R,G,B) with another.
        Accepts hex strings or tuples.
        """
        cmd = ReplaceColor(old_color, new_color)
        self._execute_command(cmd, f"replace_color {old_color} {new_color}")

    def mirror(self, direction="horizontal"):
        """Mirrors the image horizontally or vertically."""
        cmd = Mirror(direction)
        self._execute_command(cmd, f"mirror {direction}")

    def crop(self, left, upper, right, lower):
        """Crops the image to a bounding box."""
        cmd = Crop(left, upper, right, lower)
        self._execute_command(cmd, f"crop {left} {upper} {right} {lower}")

    def resize_canvas(self, width, height, fill_index=0, fill_color=(0,0,0,0)):
        """Resizes canvas without scaling image (anchored top-left)."""
        cmd = ResizeCanvas(width, height, fill_index, fill_color)
        self._execute_command(cmd, f"resize_canvas {width} {height}")

    def draw_line(self, x0, y0, x1, y1, color):
        """Draws a 1px Bresenham line between (x0, y0) and (x1, y1)."""
        cmd = DrawLine(x0, y0, x1, y1, color)
        self._execute_command(cmd, f"draw_line {x0} {y0} {x1} {y1}")

    def draw_rect(self, x0, y0, x1, y1, color, fill=True):
        """Draws a filled or outlined rectangle."""
        cmd = DrawRect(x0, y0, x1, y1, color, fill=fill)
        self._execute_command(cmd, f"draw_rect {x0} {y0} {x1} {y1}")

    def draw_ellipse(self, x0, y0, x1, y1, color, fill=True):
        """Draws a filled or outlined pixel-art ellipse."""
        cmd = DrawEllipse(x0, y0, x1, y1, color, fill=fill)
        self._execute_command(cmd, f"draw_ellipse {x0} {y0} {x1} {y1}")

    def flood_fill(self, x, y, color):
        """Contiguous 4-way flood fill starting at (x, y)."""
        cmd = FloodFill(x, y, color)
        self._execute_command(cmd, f"flood_fill {x} {y}")

    def generate_outline(self, color="#000000", mode="outside"):
        """Deterministically generates a 1px outline ('outside' or 'inside') around non-transparent pixels."""
        cmd = GenerateOutline(color=color, mode=mode)
        self._execute_command(cmd, f"generate_outline {color} {mode}")

    def apply_ascii_grid(self, grid, legend, offset_x=0, offset_y=0, transparent_behavior="clear"):
        """Paints a 2D ASCII character grid onto the document."""
        cmd = ApplyAsciiGrid(grid, legend, offset_x=offset_x, offset_y=offset_y, transparent_behavior=transparent_behavior)
        self._execute_command(cmd, "apply_ascii_grid")

    def to_ascii_grid(self, include_legend=True):
        """Returns the current document's 2D ASCII character grid and color legend."""
        analysis = self.analyze(self.document)
        return analysis.to_ascii_grid(include_legend=include_legend)

    def apply_shading(self, light_dir="top_left", intensity=0.22):
        """Applies directional pixel-art highlights and shadows to interior pixels."""
        cmd = ApplyShading(light_dir=light_dir, intensity=intensity)
        self._execute_command(cmd, f"apply_shading {light_dir}")

    def generate_color_ramp(self, base_color, steps=4, hue_shift=0.04):
        """Generates a hue-shifted pixel art color ramp from darkest shadow to brightest highlight."""
        return PaletteOperations.generate_color_ramp(base_color, steps=steps, hue_shift=hue_shift)

    def undo(self):
        """Undoes the last action."""
        return self.document.undo()

    def redo(self):
        """Redoes the last undone action."""
        return self.document.redo()

    def validate(self):
        """Runs validation checks and returns the result."""
        from .core.validation import validate_document
        return validate_document(self.document)

    # Core Reasoning Engine capabilities exposed via Workbench

    def analyze(self, target=None):
        """Analyzes a sprite conceptually. Defaults to the active document."""
        return self.engine.analyze(target or self.document)

    def review(self, target=None, style_reference=None, expected_size=None):
        """Reviews a sprite for structural and artistic flaws. Defaults to active document."""
        return self.engine.review(target or self.document, style_reference, expected_size)

    def repair(self, target=None):
        """Deterministically repairs common pixel-art flaws. Defaults to active document."""
        return self.engine.repair(target or self.document)

    def compare(self, reference, target=None):
        """Compares the current sprite conceptually against a reference."""
        return self.engine.compare(target or self.document, reference)

    def construct(self, prompt, **kwargs):
        """Generates/constructs a new sprite draft."""
        return self.engine.construct(prompt=prompt, **kwargs)

    def accept(self, draft):
        """Accepts a draft and replaces the active document."""
        self.open_document(draft.document)

    def select_region(self, region_name: str, target=None) -> set:
        """
        Returns the coordinates of the requested semantic region for the target.
        Defaults to the active document.
        """
        return self.engine.select_region(target or self.document, region_name)
