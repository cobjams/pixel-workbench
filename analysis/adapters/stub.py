import random
from typing import Tuple, Dict, Any, Optional
from PIL import Image

from ...core.document import Document
from ..draft import SpriteDraft
from .base import ConstructionProvider

class StubProvider(ConstructionProvider):
    """
    A simple stub generator that produces noise or basic shapes.
    Useful for testing the plugin architecture without a real AI backend.
    """
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed

    def construct_sprite(
        self,
        prompt: str,
        size: Tuple[int, int] = (16, 16),
        style_context: Optional[Dict[str, Any]] = None,
        palette_context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> SpriteDraft:
        if self.seed is not None:
            random.seed(self.seed)

        width, height = size

        # Create an RGBA image filled with transparency
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        pixels = img.load()

        # Generate some noise to represent a draft sprite
        for y in range(height):
            for x in range(width):
                # Simple circle constraint to make it look a bit like a sprite
                cx, cy = width / 2, height / 2
                dist = ((x - cx)**2 + (y - cy)**2)**0.5

                if dist < min(width, height) / 2:
                    r = random.randint(50, 255)
                    g = random.randint(50, 255)
                    b = random.randint(50, 255)
                    pixels[x, y] = (r, g, b, 255)

        document = Document()
        document.image = img
        document.original_mode = "RGBA"
        # document history is naturally empty for a new draft

        return SpriteDraft(
            document=document,
            prompt=prompt,
            constructor="StubProvider",
            model="local-stub",
        )
