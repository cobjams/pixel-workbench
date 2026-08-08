import time
from typing import Tuple, Dict, Any, Optional
from PIL import Image

from ...core.document import Document
from ..draft import SpriteDraft
from .base import ConstructionProvider
from ..workspace import SpriteWorkspace

class CodingAgentProvider(ConstructionProvider):
    """
    A provider designed to allow a coding agent to deterministically construct and modify
    sprites in an iterative loop (create draft -> analyze -> review -> repair).

    This does not call an external image-generation API. It gives the agent a blank slate
    or copies a reference to modify.
    """
    def construct_sprite(
        self,
        prompt: str,
        size: Tuple[int, int] = (16, 16),
        style_context: Optional[Dict[str, Any]] = None,
        palette_context: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        project_metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> SpriteWorkspace:
        """
        Creates a new, empty workspace for the agent to begin iterative construction.
        """
        width, height = size

        # Create an RGBA image filled with transparency
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        document = Document()
        document.image = img
        document.original_mode = "RGBA"

        # Populate constraints and metadata, applying defaults if needed
        workspace_constraints = constraints or {
            "required_size": size,
            "must_have_transparent_background": True
        }
        workspace_metadata = project_metadata or {
            "theme": "ball bearing factory",
            "terminology": "janitor, mop, overalls"
        }

        # Initialize the workspace
        workspace = SpriteWorkspace(
            document=document,
            constraints=workspace_constraints,
            project_metadata=workspace_metadata
        )

        # SpriteDraft context could be added if needed, but per prompt we return SpriteWorkspace directly
        return workspace
