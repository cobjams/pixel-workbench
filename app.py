from .core.document import Document
from .core.commands import (
    PaintIndex,
    PaintColor,
    ReplaceIndex,
    ReplaceColor,
    Mirror,
    Crop,
    ResizeCanvas
)

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

    def generate(self, prompt, **kwargs):
        """Generates/constructs a new sprite draft."""
        return self.engine.generate(prompt=prompt, **kwargs)

    def accept(self, draft):
        """Accepts a draft and replaces the active document."""
        self.open_document(draft.document)
