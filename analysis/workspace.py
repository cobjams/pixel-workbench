from typing import Dict, Any, Optional
from ..app import Workbench
from ..core.document import Document

class SpriteWorkspace:
    """
    Unified context object and primary mental model for autonomous coding agents
    interacting with the Pixel Workbench.
    """
    def __init__(
        self,
        document: Document,
        constraints: Optional[Dict[str, Any]] = None,
        project_metadata: Optional[Dict[str, Any]] = None
    ):
        self.workbench = Workbench()
        self.workbench.open_document(document)

        self.document = self.workbench.document
        self.history = self.document.history

        self.constraints = constraints or {}
        self.project_metadata = project_metadata or {}

        self.commands = {
            "paint_index": self.workbench.paint_index,
            "paint_color": self.workbench.paint_color,
            "replace_index": self.workbench.replace_index,
            "replace_color": self.workbench.replace_color,
            "mirror": self.workbench.mirror,
            "crop": self.workbench.crop,
            "resize_canvas": self.workbench.resize_canvas,
            "draw_line": self.workbench.draw_line,
            "draw_rect": self.workbench.draw_rect,
            "draw_ellipse": self.workbench.draw_ellipse,
            "flood_fill": self.workbench.flood_fill,
            "generate_outline": self.workbench.generate_outline,
            "apply_ascii_grid": self.workbench.apply_ascii_grid,
            "apply_shading": self.workbench.apply_shading,
            "generate_color_ramp": self.workbench.generate_color_ramp,
            "undo": self.workbench.undo,
            "redo": self.workbench.redo,
            "repair": self.workbench.repair,
        }

        self.analysis = None
        self.validation = None

        # Initial refresh
        self.refresh()

    def refresh(self):
        """
        Updates the semantic state (analysis) and validation report based on
        the current document pixel data.
        """
        self.analysis = self.workbench.analyze(self.document)
        # Workbench.review can take expected_size from constraints if available
        expected_size = self.constraints.get("required_size", None)
        self.validation = self.workbench.review(self.document, expected_size=expected_size)

    def update_state(self):
        """Alias for refresh."""
        self.refresh()

    def to_ascii_grid(self, include_legend: bool = True) -> Dict[str, Any]:
        """Returns a 2D ASCII character grid and legend for the current sprite."""
        self.refresh()
        return self.analysis.to_ascii_grid(include_legend=include_legend)

    def apply_ascii_grid(
        self,
        grid,
        legend: Dict[str, Any],
        offset_x: int = 0,
        offset_y: int = 0,
        transparent_behavior: str = "clear"
    ):
        """Paints a 2D ASCII character grid onto the document and refreshes workspace state."""
        self.workbench.apply_ascii_grid(
            grid,
            legend,
            offset_x=offset_x,
            offset_y=offset_y,
            transparent_behavior=transparent_behavior
        )
        self.refresh()

    def summary(self, include_grid: bool = True) -> Dict[str, Any]:
        """Returns a complete JSON-serializable mental model of the workspace."""
        self.refresh()
        return {
            "constraints": self.constraints,
            "project_metadata": self.project_metadata,
            "analysis": self.analysis.to_dict(include_grid=include_grid),
            "validation": self.validation,
            "can_undo": self.history.can_undo(),
            "can_redo": self.history.can_redo(),
        }
