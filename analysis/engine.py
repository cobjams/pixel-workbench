from typing import Tuple, Dict, Any, Optional, Union
from .draft import SpriteDraft
from .adapters.base import AIProvider
from .adapters.stub import StubProvider
from .style_analyzer import analyze_style
from .palette_matcher import match_palette, quantize_to_palette
from .sprite_reviewer import review_sprite
from ..core.document import Document
from .sprite_analysis import SpriteAnalysis
from PIL import Image
import os

class ReasoningEngine:
    """
    Core semantic reasoning and execution layer for the Pixel Workbench.
    Exposes capabilities like analyze, review, repair, and generate.
    """
    def __init__(self, provider: Optional[AIProvider] = None):
        self.provider = provider or StubProvider()

    def generate(
        self,
        prompt: str,
        size: Tuple[int, int] = (16, 16),
        style_reference: Optional[str] = None,
        palette_reference: Optional[str] = None,
        transparency: bool = True,
        **kwargs
    ) -> SpriteDraft:
        """Constructs a draft sprite using the configured provider."""
        style_context = None
        if style_reference:
            style_context = analyze_style(style_reference)

        palette_context = None
        if palette_reference:
            pass

        return self.provider.generate_sprite(
            prompt=prompt,
            size=size,
            style_context=style_context,
            palette_context=palette_context,
            **kwargs
        )

    def analyze(self, target: Union[str, Document, SpriteDraft]) -> Union[Dict[str, Any], SpriteAnalysis]:
        """
        Analyzes a target (file path, Document, or Draft) and returns structured semantic metadata.
        For a single Document or SpriteDraft (or a path to a single image), returns a SpriteAnalysis object.
        For a path to a directory, returns a dictionary via analyze_style().
        """
        if isinstance(target, str):
            if os.path.isdir(target):
                return analyze_style(target)
            else:
                # Target is a file path to a single image
                img = Image.open(target)
                return SpriteAnalysis(img)
        elif isinstance(target, SpriteDraft):
            return SpriteAnalysis(target.document.image)
        elif isinstance(target, Document):
             return SpriteAnalysis(target.image)

        raise ValueError("Invalid target for analysis.")

    def review(self, target: Union[SpriteDraft, Document], style_reference: Optional[str] = None, expected_size: Optional[tuple] = None) -> Dict[str, Any]:
        """Reviews a draft or document against style/palette constraints."""
        draft = target if isinstance(target, SpriteDraft) else SpriteDraft(document=target)
        return review_sprite(draft, style_reference, expected_size)

    def repair(self, target: Union[SpriteDraft, Document]) -> Dict[str, Any]:
        """
        Automatically fixes common issues (e.g. noise, palette inconsistencies).
        Returns a report of what was repaired.
        """
        # Stub for the repair capability
        return {"repaired": True, "actions": ["Stub repair logic executed."]}

    def compare(self, target: Union[SpriteDraft, Document], reference: Union[str, Document]) -> Dict[str, Any]:
        """Compares a sprite against a reference to produce diff semantics."""
        # Stub for comparison capability
        return {"similarity_score": 0.0, "differences": []}
