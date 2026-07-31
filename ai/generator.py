from typing import Tuple, Dict, Any, Optional
from .draft import SpriteDraft
from .adapters.base import AIProvider
from .adapters.stub import StubProvider
from .style_analyzer import analyze_style
from .palette_matcher import match_palette, quantize_to_palette
from .sprite_reviewer import review_sprite

class AIManager:
    """
    Facade for the AI generation capabilities.
    Exposes a clean API for generating, analyzing, matching, and reviewing sprites.
    """
    def __init__(self, provider: Optional[AIProvider] = None):
        # Default to the stub provider for now
        self.provider = provider or StubProvider()

    def generate_sprite(
        self,
        prompt: str,
        size: Tuple[int, int] = (16, 16),
        style_reference: Optional[str] = None,
        palette_reference: Optional[str] = None,
        transparency: bool = True,
        **kwargs
    ) -> SpriteDraft:
        """
        Generates a draft sprite using the configured AI provider.
        """
        style_context = None
        if style_reference:
            style_context = analyze_style(style_reference)

        palette_context = None
        if palette_reference:
            # We just need the context for the prompt/generation, not the actual quantization here
            pass

        draft = self.provider.generate_sprite(
            prompt=prompt,
            size=size,
            style_context=style_context,
            palette_context=palette_context,
            **kwargs
        )

        return draft

    def analyze_style(self, path: str) -> Dict[str, Any]:
        """Analyzes a directory or file and returns style metrics."""
        return analyze_style(path)

    def match_palette(self, image, reference_palette):
        return match_palette(image, reference_palette)

    def quantize_to_palette(self, image, palette_colors):
        return quantize_to_palette(image, palette_colors)

    def review_sprite(self, draft: SpriteDraft, style_reference: Optional[str] = None, expected_size: Optional[tuple] = None) -> Dict[str, Any]:
        """Reviews a generated draft."""
        return review_sprite(draft, style_reference, expected_size)
