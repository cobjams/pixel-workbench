from typing import List, Dict, Any, Union
from ...core.document import Document
from ..sprite_analysis import SpriteAnalysis
from .base import RepairRule
from ..draft import SpriteDraft
from .rules import RemoveIsolatedPixelsRule, StandardizeOutlineColorRule, NormalizePaletteRule, RemoveJaggiesRule

class RepairEngine:
    def __init__(self, rules: List[RepairRule] = None, include_jaggies: bool = False):
        if rules is not None:
            self.rules: List[RepairRule] = rules
        else:
            self.rules = [
                RemoveIsolatedPixelsRule(),
                StandardizeOutlineColorRule(),
                NormalizePaletteRule()
            ]
            if include_jaggies:
                self.rules.append(RemoveJaggiesRule())

    def run(self, target: Union[SpriteDraft, Document]) -> Dict[str, Any]:
        document = target.document if isinstance(target, SpriteDraft) else target

        report = {"repaired": False, "actions": []}
        state_pushed = False

        for rule in self.rules:
            # Re-analyze for each rule because previous rules might have changed the image
            analysis = SpriteAnalysis(document.image)

            if rule.applies(document, analysis):
                if not state_pushed:
                    document.push_state("repair")
                    state_pushed = True
                rule.repair(document, analysis)
                report["actions"].append(rule.explain())
                report["repaired"] = True

        return report
