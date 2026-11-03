import math
from typing import Tuple, List, Set, Dict
from ...core.document import Document
from ..sprite_analysis import SpriteAnalysis
from .base import RepairRule
from PIL import Image

class RemoveIsolatedPixelsRule(RepairRule):
    def __init__(self, max_pixels: int = 1):
        self.max_pixels = max_pixels
        self.removed_count = 0

    def applies(self, document: Document, analysis: SpriteAnalysis) -> bool:
        for component in analysis.connected_components:
            if len(component) <= self.max_pixels:
                return True
        return False

    def repair(self, document: Document, analysis: SpriteAnalysis) -> None:
        self.removed_count = 0
        pixels = document.image.load()
        for component in analysis.connected_components:
            if len(component) <= self.max_pixels:
                for x, y in component:
                    pixels[x, y] = (0, 0, 0, 0)
                    self.removed_count += 1

    def explain(self) -> str:
        return f"Removed {self.removed_count} isolated stray pixels."


class StandardizeOutlineColorRule(RepairRule):
    def __init__(self):
        self.hex_color = ""

    def applies(self, document: Document, analysis: SpriteAnalysis) -> bool:
        if not analysis.outline:
            return False

        pixels = document.image.load()
        colors = set()

        for x, y in analysis.outline:
            color = pixels[x, y]
            if color[3] > 0:
                colors.add(color)

        return len(colors) > 1

    def repair(self, document: Document, analysis: SpriteAnalysis) -> None:
        pixels = document.image.load()
        color_counts = {}

        for x, y in analysis.outline:
            color = pixels[x, y]
            if color[3] > 0:
                color_counts[color] = color_counts.get(color, 0) + 1

        if not color_counts:
            return

        # Find the most common color
        most_common_color = max(color_counts.items(), key=lambda item: item[1])[0]
        self.hex_color = "#{:02x}{:02x}{:02x}".format(most_common_color[0], most_common_color[1], most_common_color[2])

        # Standardize the outline
        for x, y in analysis.outline:
            if pixels[x, y][3] > 0:
                pixels[x, y] = most_common_color

    def explain(self) -> str:
        return f"Standardized outline color to {self.hex_color}."


class NormalizePaletteRule(RepairRule):
    def __init__(self, threshold: float = 10.0):
        self.threshold = threshold
        self.merged = False

    def applies(self, document: Document, analysis: SpriteAnalysis) -> bool:
        palette = analysis.palette
        for i in range(len(palette)):
            for j in range(i + 1, len(palette)):
                c1, c2 = palette[i], palette[j]
                if self._distance(c1, c2) < self.threshold:
                    return True
        return False

    def _distance(self, c1: Tuple[int, int, int, int], c2: Tuple[int, int, int, int]) -> float:
        return math.sqrt((c1[0] - c2[0])**2 + (c1[1] - c2[1])**2 + (c1[2] - c2[2])**2)

    def repair(self, document: Document, analysis: SpriteAnalysis) -> None:
        self.merged = True
        pixels = document.image.load()
        palette = analysis.palette
        width, height = document.image.size

        color_counts = {}
        for y in range(height):
            for x in range(width):
                color = pixels[x, y]
                if color[3] > 0:
                    color_counts[color] = color_counts.get(color, 0) + 1

        replacements = {}
        # Simple clustering: merge near colors into the most common one in the cluster
        for i in range(len(palette)):
            for j in range(i + 1, len(palette)):
                c1, c2 = palette[i], palette[j]
                if self._distance(c1, c2) < self.threshold:
                    count1 = color_counts.get(c1, 0)
                    count2 = color_counts.get(c2, 0)

                    if count1 >= count2:
                        replacements[c2] = replacements.get(c1, c1)
                    else:
                        replacements[c1] = replacements.get(c2, c2)

        for y in range(height):
            for x in range(width):
                color = pixels[x, y]
                if color in replacements:
                    pixels[x, y] = replacements[color]

    def explain(self) -> str:
        return "Merged near-duplicate colors in the palette."


class RemoveJaggiesRule(RepairRule):
    """
    Detects and removes 1px L-shaped corner 'doubles' (staircase artifacts) on the sprite outline.
    Specifically, an outline pixel (x, y) is a removable corner double if:
      - It has exactly two orthogonal (4-way) neighbors in the outline of the same color,
        forming a 90-degree corner: e.g. (x+dx, y) and (x, y+dy) are in the outline with the same color,
      - Those two neighbors are diagonally adjacent to each other,
      - The opposite side of (x, y) — i.e., (x-dx, y) and (x, y-dy) — are both transparent,
      - And the interior diagonal (x+dx, y+dy) is opaque (so removing (x, y) exposes the clean diagonal step).
    """
    def __init__(self):
        self.removed_coords: List[Tuple[int, int]] = []

    def _find_corner_doubles(self, document: Document, analysis: SpriteAnalysis) -> List[Tuple[int, int]]:
        w, h = document.image.size
        rgba = document.image.convert("RGBA")
        pixels = rgba.load()
        outline = analysis.outline
        candidates = []

        def is_transparent(px, py):
            if not (0 <= px < w and 0 <= py < h):
                return True
            return pixels[px, py][3] == 0

        for x, y in sorted(outline):
            color = pixels[x, y]
            if color[3] == 0:
                continue
            for dx in (-1, 1):
                for dy in (-1, 1):
                    n1 = (x + dx, y)
                    n2 = (x, y + dy)
                    diag_in = (x + dx, y + dy)
                    opp1 = (x - dx, y)
                    opp2 = (x, y - dy)
                    opp_diag = (x - dx, y - dy)
                    if (
                        n1 in outline
                        and n2 in outline
                        and pixels[n1[0], n1[1]] == color
                        and pixels[n2[0], n2[1]] == color
                        and 0 <= diag_in[0] < w
                        and 0 <= diag_in[1] < h
                        and pixels[diag_in[0], diag_in[1]][3] > 0
                        and is_transparent(*opp1)
                        and is_transparent(*opp2)
                        and is_transparent(*opp_diag)
                    ):
                        candidates.append((x, y))
                        break
                else:
                    continue
                break
        return candidates

    def applies(self, document: Document, analysis: SpriteAnalysis) -> bool:
        return len(self._find_corner_doubles(document, analysis)) > 0

    def repair(self, document: Document, analysis: SpriteAnalysis) -> None:
        self.removed_coords = self._find_corner_doubles(document, analysis)
        pixels = document.image.load()
        clear_val = 0 if document.mode == "P" else ((0, 0, 0, 0) if document.mode == "RGBA" else (0, 0, 0))
        for x, y in self.removed_coords:
            pixels[x, y] = clear_val

    def explain(self) -> str:
        return f"Removed {len(self.removed_coords)} L-corner double pixels (jaggies) at {self.removed_coords}."

