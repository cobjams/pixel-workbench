import time
from typing import Tuple, Dict, Any, Optional
from PIL import Image

from ...core.document import Document
from ..draft import SpriteDraft
from .base import AIProvider

class CodingAgentProvider(AIProvider):
    """
    A provider designed to allow a coding agent to deterministically construct and modify
    sprites in an iterative loop (create draft -> analyze -> review -> repair).

    This does not call an external image-generation API. It gives the agent a blank slate
    or copies a reference to modify.
    """
    def generate_sprite(
        self,
        prompt: str,
        size: Tuple[int, int] = (16, 16),
        style_context: Optional[Dict[str, Any]] = None,
        palette_context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> SpriteDraft:
        """
        Creates a new, empty draft sprite for the agent to begin iterative construction.
        """
        width, height = size

        # Create an RGBA image filled with transparency
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        document = Document()
        document.image = img
        document.original_mode = "RGBA"

        return SpriteDraft(
            document=document,
            prompt=prompt,
            generator="CodingAgentProvider",
            model="agent-iterative",
        )
