from typing import Tuple, Dict, Any, Optional, Union, Set
from .draft import SpriteDraft
from .adapters.base import ConstructionProvider
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
    def __init__(self, provider: Optional[ConstructionProvider] = None):
        self.provider = provider or StubProvider()

    def construct(
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

        return self.provider.construct_sprite(
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

    def repair(
        self,
        target: Union[SpriteDraft, Document],
        dry_run: bool = False,
        safe: bool = True,
        include_jaggies: bool = False,
        rule_names: Optional[list] = None,
        protect_coords: Optional[set] = None
    ) -> Dict[str, Any]:
        """
        Automatically fixes common issues (e.g. noise, palette inconsistencies).
        Supports dry_run=True, safe=True (preserving accents/symmetric details),
        and coordinate protection.
        """
        from .repair.engine import RepairEngine
        engine = RepairEngine(
            include_jaggies=include_jaggies,
            safe=safe,
            protect_coords=protect_coords,
            rule_names=rule_names,
        )
        return engine.run(target, dry_run=dry_run)

    def regression_report(
        self,
        before: Union[SpriteDraft, Document, str],
        after: Union[SpriteDraft, Document, str],
        constraints: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generates a semantic visual regression and pixel-art QA report between before and after.
        """
        from .regression import generate_regression_report
        b_doc = before.document if isinstance(before, SpriteDraft) else before
        a_doc = after.document if isinstance(after, SpriteDraft) else after
        return generate_regression_report(b_doc, a_doc, constraints=constraints)

    def compare(self, target: Union[SpriteDraft, Document, str], reference: Union[str, Document, SpriteDraft]) -> Dict[str, Any]:
        """Compares a sprite against a reference to produce diff semantics."""
        from ..tools.compare import compare_images

        def _get_image(obj):
            if isinstance(obj, str):
                return Image.open(obj)
            elif isinstance(obj, SpriteDraft):
                return obj.document.image
            elif isinstance(obj, Document):
                return obj.image
            elif isinstance(obj, Image.Image):
                return obj
            raise ValueError("Invalid target or reference for comparison.")

        target_img = _get_image(target)
        ref_img = _get_image(reference)
        diff_report = compare_images(ref_img, target_img)
        total_pixels = max(1, max(target_img.width, ref_img.width) * max(target_img.height, ref_img.height))
        similarity = max(0.0, 1.0 - (diff_report["changed_pixels"] / total_pixels))
        diff_report["similarity_score"] = round(similarity, 4)
        return diff_report

    def select_region(self, target: Union[str, Document, SpriteDraft], region_name: str) -> set:
        """
        Analyzes the target and returns the coordinates of the requested semantic region.
        """
        analysis = self.analyze(target)
        if hasattr(analysis, "get_region"):
            return analysis.get_region(region_name)
        return set()
