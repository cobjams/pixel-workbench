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
