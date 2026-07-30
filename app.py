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

    def open(self, filepath):
        """Loads an image into the document."""
        self.document.load(filepath)

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
