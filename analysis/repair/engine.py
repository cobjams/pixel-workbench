from typing import List, Dict, Any, Union, Optional, Set, Tuple
from ...core.document import Document
from ..sprite_analysis import SpriteAnalysis
from .base import RepairRule
from ..draft import SpriteDraft
from .rules import RemoveIsolatedPixelsRule, StandardizeOutlineColorRule, NormalizePaletteRule, RemoveJaggiesRule


class RepairEngine:
    def __init__(
        self,
        rules: Optional[List[RepairRule]] = None,
        include_jaggies: bool = False,
        safe: bool = True,
        protect_coords: Optional[Set[Tuple[int, int]]] = None,
        rule_names: Optional[List[str]] = None
    ):
        self.safe = safe
        self.protect_coords: Set[Tuple[int, int]] = set(protect_coords) if protect_coords else set()

        if rules is not None:
            self.rules: List[RepairRule] = rules
        else:
            default_rules: List[RepairRule] = [
                RemoveIsolatedPixelsRule(
                    preserve_symmetric=safe,
                    preserve_particles=safe,
                    protect_coords=self.protect_coords
                ),
                StandardizeOutlineColorRule(
                    preserve_accents=safe,
                    protect_coords=self.protect_coords
                ),
                NormalizePaletteRule()
            ]
            if include_jaggies or (rule_names and "remove_jaggies" in rule_names):
                default_rules.append(RemoveJaggiesRule(protect_coords=self.protect_coords))

            if rule_names is not None:
                allowed = set(rule_names)
                default_rules = [r for r in default_rules if getattr(r, "name", "") in allowed]

            self.rules = default_rules

    def run(self, target: Union[SpriteDraft, Document], dry_run: bool = False) -> Dict[str, Any]:
        document = target.document if isinstance(target, SpriteDraft) else target

        report: Dict[str, Any] = {
            "repaired": False,
            "dry_run": dry_run,
            "actions": [],
            "modified_pixels": [],
            "preserved_details": [],
        }

        if not document or not document.image:
            return report

        # Work on a clone if dry_run=True so the original document is never mutated
        work_doc = Document()
        work_doc.image = document.image.copy() if dry_run else document.image
        work_doc.original_mode = document.original_mode or document.image.mode

        state_pushed = False

        for rule in self.rules:
            analysis = SpriteAnalysis(work_doc.image)
            applies = rule.applies(work_doc, analysis)

            # Record any preserved details discovered during rule evaluation
            rule_name = getattr(rule, "name", rule.__class__.__name__)
            if hasattr(rule, "preserved_coords") and rule.preserved_coords:
                report["preserved_details"].append({
                    "rule": rule_name,
                    "reason": "symmetric_or_particle_or_protected",
                    "coords": [list(c) for c in rule.preserved_coords]
                })
            if hasattr(rule, "preserved_accents") and rule.preserved_accents:
                report["preserved_details"].append({
                    "rule": rule_name,
                    "reason": "intentional_outline_accent_or_selout",
                    "coords": [list(c) for c in rule.preserved_accents]
                })

            if applies:
                if not dry_run and not state_pushed:
                    document.push_state("repair")
                    state_pushed = True

                before_rgba = work_doc.image.convert("RGBA")
                before_px = before_rgba.load()

                rule.repair(work_doc, analysis)

                after_rgba = work_doc.image.convert("RGBA")
                after_px = after_rgba.load()
                w, h = work_doc.image.size
                for y in range(h):
                    for x in range(w):
                        if before_px[x, y] != after_px[x, y]:
                            report["modified_pixels"].append({
                                "coord": [x, y],
                                "rule": rule_name,
                                "old_rgba": list(before_px[x, y]),
                                "new_rgba": list(after_px[x, y]),
                            })

                report["actions"].append(rule.explain())
                report["repaired"] = True

        return report
