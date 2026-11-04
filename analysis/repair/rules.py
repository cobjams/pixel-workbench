import math
from typing import Tuple, List, Set, Dict, Optional, Any
from ...core.document import Document
from ..sprite_analysis import SpriteAnalysis
from .base import RepairRule
from PIL import Image


class RemoveIsolatedPixelsRule(RepairRule):
    """
    Removes stray isolated single-pixel components while preserving:
      - 1px interior details (eyes, specular highlights, buttons) that are adjacent to opaque pixels
      - Explicitly protected coordinates (protect_coords)
      - Horizontally symmetric 1px detached details (e.g., twin sparks/particles) when preserve_symmetric=True
      - Repeated particle motifs (>= 3 detached pixels of the exact same color, e.g. starfields) when preserve_particles=True
    """
    name = "isolated_pixels"

    def __init__(
        self,
        max_pixels: int = 1,
        preserve_symmetric: bool = True,
        preserve_particles: bool = True,
        protect_coords: Optional[Set[Tuple[int, int]]] = None
    ):
        self.max_pixels = max_pixels
        self.preserve_symmetric = preserve_symmetric
        self.preserve_particles = preserve_particles
        self.protect_coords: Set[Tuple[int, int]] = set(protect_coords) if protect_coords else set()
        self.removed_count = 0
        self.removed_coords: List[Tuple[int, int]] = []
        self.preserved_coords: List[Tuple[int, int]] = []

    def _evaluate_candidates(
        self, document: Document, analysis: SpriteAnalysis
    ) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        w, h = document.image.size
        rgba = document.image.convert("RGBA")
        pixels = rgba.load()

        # Gather all small detached components (8-way connected in alpha)
        raw_small_components: List[Set[Tuple[int, int]]] = [
            comp for comp in analysis.connected_components if len(comp) <= self.max_pixels
        ]

        # Count occurrences of each color among 1px detached components (to detect starfields/particles)
        detached_color_counts: Dict[Tuple[int, int, int, int], int] = {}
        for comp in raw_small_components:
            if len(comp) == 1:
                x, y = next(iter(comp))
                c = pixels[x, y]
                detached_color_counts[c] = detached_color_counts.get(c, 0) + 1

        to_remove: List[Tuple[int, int]] = []
        preserved: List[Tuple[int, int]] = []

        for comp in raw_small_components:
            comp_coords = sorted(comp)
            # Check if any pixel in component is explicitly protected
            if any(pt in self.protect_coords for pt in comp_coords):
                preserved.extend(comp_coords)
                continue

            if len(comp_coords) == 1:
                x, y = comp_coords[0]
                color = pixels[x, y]

                # 1. Check horizontal symmetry counterpart (e.g. symmetric floating sparks/hands)
                mirror_x = w - 1 - x
                if (
                    self.preserve_symmetric
                    and mirror_x != x
                    and 0 <= mirror_x < w
                    and pixels[mirror_x, y] == color
                ):
                    preserved.append((x, y))
                    continue

                # 2. Check repeated particle/starfield motif (>= 3 detached pixels of identical color)
                if self.preserve_particles and detached_color_counts.get(color, 0) >= 3:
                    preserved.append((x, y))
                    continue

            to_remove.extend(comp_coords)

        return sorted(to_remove), sorted(preserved)

    def applies(self, document: Document, analysis: SpriteAnalysis) -> bool:
        to_remove, preserved = self._evaluate_candidates(document, analysis)
        self.preserved_coords = preserved
        return len(to_remove) > 0

    def repair(self, document: Document, analysis: SpriteAnalysis) -> None:
        to_remove, preserved = self._evaluate_candidates(document, analysis)
        self.removed_coords = to_remove
        self.preserved_coords = preserved
        self.removed_count = len(to_remove)
        pixels = document.image.load()
        clear_val = 0 if document.mode == "P" else ((0, 0, 0, 0) if document.mode == "RGBA" else (0, 0, 0))
        for x, y in to_remove:
            pixels[x, y] = clear_val

    def explain(self) -> str:
        return f"Removed {self.removed_count} isolated stray pixels."


class StandardizeOutlineColorRule(RepairRule):
    """
    Standardizes accidental rogue outline pixels to the dominant outline color while
    preserving intentional colored accents and selective outlining (sel-out).
    """
    name = "standardize_outline"

    def __init__(
        self,
        preserve_accents: bool = True,
        near_color_threshold: float = 45.0,
        protect_coords: Optional[Set[Tuple[int, int]]] = None
    ):
        self.preserve_accents = preserve_accents
        self.near_color_threshold = near_color_threshold
        self.protect_coords: Set[Tuple[int, int]] = set(protect_coords) if protect_coords else set()
        self.hex_color = ""
        self.modified_coords: List[Tuple[int, int]] = []
        self.preserved_accents: List[Tuple[int, int]] = []

    @staticmethod
    def _color_dist(c1: Tuple[int, ...], c2: Tuple[int, ...]) -> float:
        return math.sqrt((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2 + (c1[2] - c2[2]) ** 2)

    def _analyze_outline_anomalies(
        self, document: Document, analysis: SpriteAnalysis
    ) -> Tuple[Optional[Tuple[int, ...]], List[Tuple[int, int]], List[Tuple[int, int]]]:
        if not analysis.outline:
            return None, [], []

        w, h = document.image.size
        rgba = document.image.convert("RGBA")
        pixels = rgba.load()

        color_counts: Dict[Tuple[int, int, int, int], int] = {}
        outline_set = set(analysis.outline)

        for x, y in outline_set:
            color = pixels[x, y]
            if color[3] > 0:
                color_counts[color] = color_counts.get(color, 0) + 1

        if len(color_counts) <= 1:
            return None, [], []

        most_common_color, dominant_count = max(color_counts.items(), key=lambda item: item[1])

        if not self.preserve_accents:
            to_fix = [
                (x, y)
                for x, y in sorted(outline_set)
                if pixels[x, y][3] > 0 and pixels[x, y] != most_common_color and (x, y) not in self.protect_coords
            ]
            return most_common_color, to_fix, []

        # Guard 1: Check if the sprite actually has a dedicated outline.
        # If the dominant outline color accounts for < 50% of the boundary, or if the dominant
        # outline color is also the primary interior fill color (borderless shape), do not clobber the boundary.
        interior_counts: Dict[Tuple[int, int, int, int], int] = {}
        for y in range(h):
            for x in range(w):
                if (x, y) not in outline_set and pixels[x, y][3] > 0:
                    c = pixels[x, y]
                    interior_counts[c] = interior_counts.get(c, 0) + 1

        if dominant_count / max(1, len(outline_set)) < 0.5:
            return most_common_color, [], sorted(
                (x, y) for x, y in outline_set if pixels[x, y] != most_common_color
            )

        if interior_counts:
            dominant_interior_color = max(interior_counts.items(), key=lambda item: item[1])[0]
            if dominant_interior_color == most_common_color and len(color_counts) > 1:
                # Borderless sprite where interior fill touches the edge
                return most_common_color, [], sorted(
                    (x, y) for x, y in outline_set if pixels[x, y] != most_common_color
                )

        # Group non-dominant outline pixels into 8-connected same-color outline segments
        non_dom_pixels = {
            (x, y)
            for x, y in outline_set
            if pixels[x, y][3] > 0 and pixels[x, y] != most_common_color
        }
        visited: Set[Tuple[int, int]] = set()
        to_fix: List[Tuple[int, int]] = []
        preserved: List[Tuple[int, int]] = []

        for pt in sorted(non_dom_pixels):
            if pt in visited:
                continue
            seg = set()
            queue = [pt]
            visited.add(pt)
            seg_color = pixels[pt[0], pt[1]]

            while queue:
                cx, cy = queue.pop(0)
                seg.add((cx, cy))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = cx + dx, cy + dy
                        if (nx, ny) in non_dom_pixels and (nx, ny) not in visited:
                            if pixels[nx, ny] == seg_color:
                                visited.add((nx, ny))
                                queue.append((nx, ny))

            seg_coords = sorted(seg)
            if any(p in self.protect_coords for p in seg_coords):
                preserved.extend(seg_coords)
                continue

            # If color is very close to the dominant outline color, it's brush/compression noise -> fix it
            if self._color_dist(seg_color, most_common_color) <= self.near_color_threshold:
                to_fix.extend(seg_coords)
                continue

            # Check if this outline segment is an intentional multi-pixel accent (>= 2 contiguous pixels)
            if len(seg_coords) >= 2:
                preserved.extend(seg_coords)
                continue

            # Single-pixel distinct color on the outline: check if it is horizontally symmetric
            x, y = seg_coords[0]
            mirror_x = w - 1 - x
            if mirror_x != x and (mirror_x, y) in non_dom_pixels and pixels[mirror_x, y] == seg_color:
                preserved.append((x, y))
                continue

            # Otherwise, it is a single asymmetric rogue outline pixel -> standardize it
            to_fix.append((x, y))

        return most_common_color, sorted(to_fix), sorted(preserved)

    def applies(self, document: Document, analysis: SpriteAnalysis) -> bool:
        _, to_fix, preserved = self._analyze_outline_anomalies(document, analysis)
        self.preserved_accents = preserved
        return len(to_fix) > 0

    def repair(self, document: Document, analysis: SpriteAnalysis) -> None:
        most_common_color, to_fix, preserved = self._analyze_outline_anomalies(document, analysis)
        self.modified_coords = to_fix
        self.preserved_accents = preserved
        if not most_common_color or not to_fix:
            return

        self.hex_color = "#{:02x}{:02x}{:02x}".format(
            most_common_color[0], most_common_color[1], most_common_color[2]
        )
        pixels = document.image.load()
        target_val = most_common_color if document.mode == "RGBA" else most_common_color[:3]
        for x, y in to_fix:
            pixels[x, y] = target_val

    def explain(self) -> str:
        return f"Standardized outline color to {self.hex_color}."


class NormalizePaletteRule(RepairRule):
    name = "normalize_palette"

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
    name = "remove_jaggies"

    def __init__(self, protect_coords: Optional[Set[Tuple[int, int]]] = None):
        self.protect_coords: Set[Tuple[int, int]] = set(protect_coords) if protect_coords else set()
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
            if (x, y) in self.protect_coords:
                continue
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

