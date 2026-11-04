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
        self._clusters: Optional[List[Dict[str, Any]]] = None

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

    @property
    def clusters(self) -> List[Dict[str, Any]]:
        """
        Returns 4-way color-connected clusters of opaque pixels.
        Each cluster contains:
          - color: (r, g, b, a)
          - hex: hex color string
          - pixels: Set[(x, y)]
          - size: int
          - touches_transparency: bool
          - is_interior_detail: bool (True if completely surrounded by opaque pixels, e.g. an eye or highlight)
        """
        if self._clusters is None:
            self._clusters = self._compute_color_clusters()
        return self._clusters

    def _compute_color_clusters(self) -> List[Dict[str, Any]]:
        visited = set()
        clusters = []
        for y in range(self._height):
            for x in range(self._width):
                pixel = self._pixels[x, y]
                if (x, y) not in visited and pixel[3] > 0:
                    comp = set()
                    queue = [(x, y)]
                    visited.add((x, y))
                    touches_trans = False

                    while queue:
                        cx, cy = queue.pop(0)
                        comp.add((cx, cy))
                        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nx, ny = cx + dx, cy + dy
                            if nx < 0 or nx >= self._width or ny < 0 or ny >= self._height:
                                touches_trans = True
                            else:
                                npix = self._pixels[nx, ny]
                                if npix[3] == 0:
                                    touches_trans = True
                                elif (nx, ny) not in visited and npix == pixel:
                                    visited.add((nx, ny))
                                    queue.append((nx, ny))

                    r, g, b, a = pixel
                    hex_c = f"#{r:02x}{g:02x}{b:02x}" if a == 255 else f"#{r:02x}{g:02x}{b:02x}{a:02x}"
                    clusters.append({
                        "color": pixel,
                        "hex": hex_c,
                        "pixels": comp,
                        "size": len(comp),
                        "touches_transparency": touches_trans,
                        "is_interior_detail": not touches_trans,
                    })
        return clusters

    @property
    def semantic_regions(self) -> Dict[str, Set[Tuple[int, int]]]:
        if not hasattr(self, '_semantic_regions') or self._semantic_regions is None:
            from .decomposition import extract_semantic_regions
            self._semantic_regions = extract_semantic_regions(self)
        return self._semantic_regions

    def get_region(self, name: str) -> Set[Tuple[int, int]]:
        return self.semantic_regions.get(name, set())

    def to_ascii_grid(self, include_legend: bool = True) -> Dict[str, Any]:
        """
        Converts the sprite into a 2D ASCII character grid and color legend
        so coding agents can read and reason about spatial structure directly.
        Guaranteed lossless (1 character per pixel, no palette collisions).
        """
        symbols = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz@#$%&*+=?~^!/:;<>|_"
        color_to_char: Dict[Tuple[int, int, int, int], str] = {}
        legend: Dict[str, str] = {".": "transparent"}
        next_sym_idx = 0

        def _alloc_symbol(idx: int) -> str:
            if idx < len(symbols):
                return symbols[idx]
            return chr(0x0100 + (idx - len(symbols)))

        rows = []
        for y in range(self._height):
            row_chars = []
            for x in range(self._width):
                pixel = self._pixels[x, y]
                if pixel[3] == 0:
                    row_chars.append(".")
                else:
                    if pixel not in color_to_char:
                        sym = _alloc_symbol(next_sym_idx)
                        next_sym_idx += 1
                        color_to_char[pixel] = sym
                        r, g, b, a = pixel
                        hex_color = f"#{r:02x}{g:02x}{b:02x}" if a == 255 else f"#{r:02x}{g:02x}{b:02x}{a:02x}"
                        legend[sym] = hex_color
                    row_chars.append(color_to_char[pixel])
            rows.append("".join(row_chars))

        result = {
            "width": self._width,
            "height": self._height,
            "grid": rows,
            "grid_text": "\n".join(rows),
        }
        if include_legend:
            result["legend"] = legend
        return result

    def to_dict(self, include_grid: bool = True) -> Dict[str, Any]:
        """
        Returns a JSON-serializable dictionary of all semantic sprite metrics.
        """
        palette_hex = [
            f"#{r:02x}{g:02x}{b:02x}" if a == 255 else f"#{r:02x}{g:02x}{b:02x}{a:02x}"
            for r, g, b, a in self.palette
        ]
        # Compute bounding box of non-transparent pixels
        non_transparent = [
            (x, y)
            for y in range(self._height)
            for x in range(self._width)
            if self._pixels[x, y][3] > 0
        ]
        bbox = None
        if non_transparent:
            xs = [p[0] for p in non_transparent]
            ys = [p[1] for p in non_transparent]
            bbox = [min(xs), min(ys), max(xs), max(ys)]

        data = {
            "size": [self._width, self._height],
            "bounding_box": bbox,
            "palette": palette_hex,
            "palette_count": len(palette_hex),
            "transparency_percentage": round(self.transparency_percentage, 2),
            "component_count": len(self.connected_components),
            "outline_pixel_count": len(self.outline),
            "symmetry": self.symmetry,
            "semantic_region_counts": {
                k: len(v) for k, v in self.semantic_regions.items()
            },
        }
        if include_grid:
            data["ascii_representation"] = self.to_ascii_grid(include_legend=True)
        return data
