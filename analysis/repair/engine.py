from typing import List, Dict, Any, Union
from pixel_workbench.core.document import Document
from pixel_workbench.analysis.sprite_analysis import SpriteAnalysis
from .base import RepairRule
from pixel_workbench.analysis.draft import SpriteDraft
from .rules import RemoveIsolatedPixelsRule, StandardizeOutlineColorRule, NormalizePaletteRule

class RepairEngine:
    def __init__(self):
        self.rules: List[RepairRule] = [
            RemoveIsolatedPixelsRule(),
            StandardizeOutlineColorRule(),
            NormalizePaletteRule()
        ]

    def run(self, target: Union[SpriteDraft, Document]) -> Dict[str, Any]:
        document = target.document if isinstance(target, SpriteDraft) else target

        report = {"repaired": False, "actions": []}

        for rule in self.rules:
            # Re-analyze for each rule because previous rules might have changed the image
            analysis = SpriteAnalysis(document.image)

            if rule.applies(document, analysis):
                rule.repair(document, analysis)
                report["actions"].append(rule.explain())
                report["repaired"] = True

        return report
