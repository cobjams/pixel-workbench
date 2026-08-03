from typing import List, Tuple, Set, Dict, Any, Optional
from PIL import Image

class SpriteAnalysis:
    """
    Semantic AST for a single sprite/image.
    Provides deterministic geometric and color data structures.
    """
    def __init__(self, image: Image.Image):
        # We ensure a standard RGBA image for predictable analysis
        self._image = image.convert("RGBA")
        self._width, self._height = self._image.size
        self._pixels = self._image.load()

        # Computed properties cache
        self._palette: Optional[List[Tuple[int, int, int, int]]] = None
        self._transparency_percentage: Optional[float] = None
        self._connected_components: Optional[List[Set[Tuple[int, int]]]] = None
        self._outline: Optional[Set[Tuple[int, int]]] = None
        self._symmetry: Optional[Dict[str, float]] = None

        # For v1, clusters will remain empty/None as requested
        self.clusters: Optional[List[Any]] = None

    @property
    def palette(self) -> List[Tuple[int, int, int, int]]:
        if self._palette is None:
            unique_colors = set()
            for y in range(self._height):
                for x in range(self._width):
                    pixel = self._pixels[x, y]
                    # We can choose to include or exclude fully transparent pixels in the palette
                    # Often, palette includes used visible colors
                    if pixel[3] > 0:
                        unique_colors.add(pixel)
            self._palette = list(unique_colors)
        return self._palette

    @property
    def transparency_percentage(self) -> float:
        if self._transparency_percentage is None:
            transparent_count = 0
            total_pixels = self._width * self._height
            if total_pixels == 0:
                return 0.0

            for y in range(self._height):
                for x in range(self._width):
                    if self._pixels[x, y][3] == 0:
                        transparent_count += 1
            self._transparency_percentage = (transparent_count / total_pixels) * 100.0
        return self._transparency_percentage

    @property
    def connected_components(self) -> List[Set[Tuple[int, int]]]:
        if self._connected_components is None:
            self._connected_components = self._compute_connected_components()
        return self._connected_components

    def _compute_connected_components(self) -> List[Set[Tuple[int, int]]]:
        visited = set()
        components = []

        for y in range(self._height):
            for x in range(self._width):
                if (x, y) not in visited and self._pixels[x, y][3] > 0:
                    component = set()
                    queue = [(x, y)]
                    visited.add((x, y))

                    while queue:
                        cx, cy = queue.pop(0)
                        component.add((cx, cy))

                        # 8-way connectivity
                        for dx in [-1, 0, 1]:
                            for dy in [-1, 0, 1]:
                                if dx == 0 and dy == 0:
                                    continue
                                nx, ny = cx + dx, cy + dy
                                if 0 <= nx < self._width and 0 <= ny < self._height:
                                    if (nx, ny) not in visited and self._pixels[nx, ny][3] > 0:
                                        visited.add((nx, ny))
                                        queue.append((nx, ny))

                    if component:
                        components.append(component)

        return components

    @property
    def outline(self) -> Set[Tuple[int, int]]:
        if self._outline is None:
            self._outline = self._compute_outline()
        return self._outline

    def _compute_outline(self) -> Set[Tuple[int, int]]:
        outline = set()
        for y in range(self._height):
            for x in range(self._width):
                if self._pixels[x, y][3] > 0:
                    # Check 4-way neighbors to see if it borders transparency or edge
                    is_outline = False
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = x + dx, y + dy
                        if nx < 0 or nx >= self._width or ny < 0 or ny >= self._height:
                            # Edge of canvas
                            is_outline = True
                            break
                        elif self._pixels[nx, ny][3] == 0:
                            # Borders transparency
                            is_outline = True
                            break

                    if is_outline:
                        outline.add((x, y))
        return outline

    @property
    def symmetry(self) -> Dict[str, float]:
        if self._symmetry is None:
            self._symmetry = self._compute_symmetry()
        return self._symmetry

    def _compute_symmetry(self) -> Dict[str, float]:
        # Horizontal symmetry (left half compared to right half)
        # Vertical symmetry (top half compared to bottom half)

        # Calculate horizontal symmetry
        h_matches = 0
        h_total = 0
        mid_x = self._width // 2
        for y in range(self._height):
            for x in range(mid_x):
                left_pixel = self._pixels[x, y]
                right_pixel = self._pixels[self._width - 1 - x, y]

                # We only consider symmetry for non-transparent pixels,
                # or if both are transparent it counts as a match if we want strict mirroring.
                # The prompt: "excluding transparent space".
                # Meaning if BOTH are transparent, maybe skip? Let's just say we compare all valid pixels,
                # but "excluding transparent space" usually means don't penalize empty space, or only consider
                # pixels where at least one side is non-transparent.
                if left_pixel[3] > 0 or right_pixel[3] > 0:
                    h_total += 1
                    if left_pixel == right_pixel:
                        h_matches += 1

        h_score = (h_matches / h_total) if h_total > 0 else 1.0

        # Calculate vertical symmetry
        v_matches = 0
        v_total = 0
        mid_y = self._height // 2
        for x in range(self._width):
            for y in range(mid_y):
                top_pixel = self._pixels[x, y]
                bottom_pixel = self._pixels[x, self._height - 1 - y]

                if top_pixel[3] > 0 or bottom_pixel[3] > 0:
                    v_total += 1
                    if top_pixel == bottom_pixel:
                        v_matches += 1

        v_score = (v_matches / v_total) if v_total > 0 else 1.0

        return {
            "horizontal": round(h_score, 2),
            "vertical": round(v_score, 2)
        }
