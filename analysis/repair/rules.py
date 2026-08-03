import math
from typing import Tuple, List, Set, Dict
from pixel_workbench.core.document import Document
from pixel_workbench.analysis.sprite_analysis import SpriteAnalysis
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
