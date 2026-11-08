from typing import Any, Dict, List, Optional, Tuple, Union
from PIL import Image
from .palette import PaletteOperations


def parse_color_value(color: Union[str, Tuple, List, int], mode: str = "RGBA", document=None):
    """Normalizes a hex string, RGB/RGBA tuple, or palette index into a Pillow pixel value."""
    if mode == "P":
        if isinstance(color, int):
            return color
        if isinstance(color, str):
            c = color.strip()
            if c.isdigit() or (c.startswith("-") and c[1:].isdigit()):
                return int(c)
            if c.lower() in ("transparent", "none", "clear", "."):
                return 0
            if c.startswith("#") and document is not None and document.image:
                palette = document.image.getpalette()
                if palette:
                    clean = c.lstrip("#")
                    if len(clean) == 3:
                        clean = "".join(ch * 2 for ch in clean)
                    if len(clean) >= 6:
                        target_rgb = tuple(int(clean[i:i+2], 16) for i in (0, 2, 4))
                        for idx in range(len(palette) // 3):
                            if (palette[idx*3], palette[idx*3+1], palette[idx*3+2]) == target_rgb:
                                return idx
                        raise ValueError(f"Color {color} not found in 'P' mode image palette.")
        try:
            return int(color)
        except (ValueError, TypeError):
            pass
    if isinstance(color, str):
        c = color.strip().lower()
        if c in ("transparent", "none", "clear", "."):
            return (0, 0, 0, 0) if mode == "RGBA" else (0, 0, 0)
        if c.startswith("#"):
            c = c.lstrip("#")
            if len(c) == 3:
                c = "".join(ch * 2 for ch in c)
            if len(c) == 6:
                rgb = tuple(int(c[i:i+2], 16) for i in (0, 2, 4))
                return (*rgb, 255) if mode == "RGBA" else rgb
            elif len(c) == 8:
                rgba = tuple(int(c[i:i+2], 16) for i in (0, 2, 4, 6))
                return rgba if mode == "RGBA" else rgba[:3]
    if isinstance(color, (tuple, list)):
        if mode == "RGBA" and len(color) == 3:
            return (int(color[0]), int(color[1]), int(color[2]), 255)
        elif mode == "RGB" and len(color) == 4:
            return (int(color[0]), int(color[1]), int(color[2]))
        return tuple(int(x) for x in color)
    return color


class Command:
    """Base class for all deterministic document commands."""
    def execute(self, document):
        raise NotImplementedError("Commands must implement execute(document)")


class PaintIndex(Command):
    """Paints a single pixel with a palette index. Document must be 'P' mode."""
    def __init__(self, x, y, index):
        self.x = int(x)
        self.y = int(y)
        self.index = int(index)

    def execute(self, document):
        if document.mode != 'P':
            raise ValueError("PaintIndex requires 'P' mode document.")
        if 0 <= self.x < document.width and 0 <= self.y < document.height:
            document.image.putpixel((self.x, self.y), self.index)


class PaintColor(Command):
    """Paints a single pixel with an RGB/RGBA tuple or hex string."""
    def __init__(self, x, y, color):
        self.x = int(x)
        self.y = int(y)
        self.raw_color = color
        self.color = self._parse_color(color)

    def _parse_color(self, color):
        if isinstance(color, str) and color.startswith('#'):
            color = color.lstrip('#')
            if len(color) == 6:
                return tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
            elif len(color) == 8:
                return tuple(int(color[i:i+2], 16) for i in (0, 2, 4, 6))
        return color

    def execute(self, document):
        if document.mode == 'P':
            raise ValueError("PaintColor cannot be used on 'P' mode. Use PaintIndex or change mode to RGBA.")
        if 0 <= self.x < document.width and 0 <= self.y < document.height:
            val = parse_color_value(self.raw_color, document.mode)
            document.image.putpixel((self.x, self.y), val)


class DrawLine(Command):
    """Draws a pixel-perfect 1px Bresenham line between (x0, y0) and (x1, y1)."""
    def __init__(self, x0, y0, x1, y1, color):
        self.x0 = int(x0)
        self.y0 = int(y0)
        self.x1 = int(x1)
        self.y1 = int(y1)
        self.color = color

    @staticmethod
    def bresenham_points(x0: int, y0: int, x1: int, y1: int) -> List[Tuple[int, int]]:
        points = []
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            points.append((x, y))
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy
        return points

    def execute(self, document):
        val = parse_color_value(self.color, document.mode, document=document)
        w, h = document.width, document.height
        pixels = document.image.load()
        for x, y in self.bresenham_points(self.x0, self.y0, self.x1, self.y1):
            if 0 <= x < w and 0 <= y < h:
                pixels[x, y] = val


class DrawRect(Command):
    """Draws a rectangle from (x0, y0) to (x1, y1) inclusive, either filled or 1px outlined."""
    def __init__(self, x0, y0, x1, y1, color, fill=True):
        self.x0 = min(int(x0), int(x1))
        self.y0 = min(int(y0), int(y1))
        self.x1 = max(int(x0), int(x1))
        self.y1 = max(int(y0), int(y1))
        self.color = color
        self.fill = bool(fill)

    def execute(self, document):
        val = parse_color_value(self.color, document.mode, document=document)
        w, h = document.width, document.height
        pixels = document.image.load()
        for y in range(self.y0, self.y1 + 1):
            for x in range(self.x0, self.x1 + 1):
                if 0 <= x < w and 0 <= y < h:
                    if self.fill or x in (self.x0, self.x1) or y in (self.y0, self.y1):
                        pixels[x, y] = val


class DrawEllipse(Command):
    """Draws a pixel-art ellipse bounded by (x0, y0, x1, y1) inclusive."""
    def __init__(self, x0, y0, x1, y1, color, fill=True):
        self.x0 = min(int(x0), int(x1))
        self.y0 = min(int(y0), int(y1))
        self.x1 = max(int(x0), int(x1))
        self.y1 = max(int(y0), int(y1))
        self.color = color
        self.fill = bool(fill)

    def execute(self, document):
        val = parse_color_value(self.color, document.mode, document=document)
        w, h = document.width, document.height
        pixels = document.image.load()
        cx = (self.x0 + self.x1) / 2.0
        cy = (self.y0 + self.y1) / 2.0
        rx = max(0.5, (self.x1 - self.x0 + 1) / 2.0)
        ry = max(0.5, (self.y1 - self.y0 + 1) / 2.0)

        inside = set()
        for y in range(self.y0, self.y1 + 1):
            for x in range(self.x0, self.x1 + 1):
                norm = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                if norm <= 1.0:
                    inside.add((x, y))

        for x, y in inside:
            if 0 <= x < w and 0 <= y < h:
                if self.fill:
                    pixels[x, y] = val
                else:
                    # Outline pixel if any 4-neighbor is outside the ellipse
                    if any((x + dx, y + dy) not in inside for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]):
                        pixels[x, y] = val


class FloodFill(Command):
    """Contiguous 4-way flood fill starting at (x, y) with the target color."""
    def __init__(self, x, y, color):
        self.x = int(x)
        self.y = int(y)
        self.color = color

    def execute(self, document):
        w, h = document.width, document.height
        if not (0 <= self.x < w and 0 <= self.y < h):
            return
        val = parse_color_value(self.color, document.mode, document=document)
        pixels = document.image.load()
        target_val = pixels[self.x, self.y]
        if target_val == val:
            return

        queue = [(self.x, self.y)]
        visited = {(self.x, self.y)}
        while queue:
            cx, cy = queue.pop(0)
            pixels[cx, cy] = val
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                    if pixels[nx, ny] == target_val:
                        visited.add((nx, ny))
                        queue.append((nx, ny))


class GenerateOutline(Command):
    """
    Deterministically generates a 1px outline around all non-transparent pixels.
    mode='outside': paints transparent pixels that are 4-connected to opaque pixels.
    mode='inside': paints opaque pixels that border transparency or canvas edge.
    """
    def __init__(self, color="#000000", mode="outside"):
        if mode not in ("outside", "inside"):
            raise ValueError("mode must be 'outside' or 'inside'")
        self.color = color
        self.mode = mode

    def execute(self, document):
        w, h = document.width, document.height
        val = parse_color_value(self.color, document.mode, document=document)
        pixels = document.image.load()
        trans_idx = document.image.info.get("transparency") if document.mode == "P" else None

        def is_opaque(x, y):
            p = pixels[x, y]
            if document.mode == "P":
                return p != trans_idx if trans_idx is not None else p != 0
            elif document.mode == "RGBA":
                return p[3] > 0
            return True

        to_paint = []
        for y in range(h):
            for x in range(w):
                opaque = is_opaque(x, y)
                if self.mode == "outside" and not opaque:
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < w and 0 <= ny < h and is_opaque(nx, ny):
                            to_paint.append((x, y))
                            break
                elif self.mode == "inside" and opaque:
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = x + dx, y + dy
                        if nx < 0 or nx >= w or ny < 0 or ny >= h or not is_opaque(nx, ny):
                            to_paint.append((x, y))
                            break

        for x, y in to_paint:
            pixels[x, y] = val


class ApplyAsciiGrid(Command):
    """
    Paints a 2D ASCII character grid onto the document at (offset_x, offset_y).
    '.' or ' ' maps to transparent (or skipped if transparent_behavior='skip').
    Preserves exact coordinates for blank rows and leading/trailing spaces when
    space-based grids or List[str] grids are provided.
    """
    def __init__(
        self,
        grid: Union[str, List[str]],
        legend: Dict[str, Any],
        offset_x: int = 0,
        offset_y: int = 0,
        transparent_behavior: str = "clear",
        preserve_whitespace: Optional[bool] = None,
        strict: bool = False
    ):
        self.legend = legend or {}
        self.offset_x = int(offset_x)
        self.offset_y = int(offset_y)
        self.transparent_behavior = transparent_behavior
        self.strict = bool(strict)

        if isinstance(grid, list):
            # Exact row list: never strip characters or drop blank rows
            lines = [str(line) for line in grid]
        elif isinstance(grid, str):
            normalized = grid.replace("\r\n", "\n").replace("\r", "\n")
            raw_lines = normalized.split("\n")

            # Determine whether spaces are significant pixel characters
            if preserve_whitespace is None:
                space_is_pixel = (" " in self.legend) or ("." not in normalized)
            else:
                space_is_pixel = bool(preserve_whitespace)

            if space_is_pixel:
                # Only drop a single leading/trailing empty line caused by triple-quoted """\n...\n"""
                if len(raw_lines) > 1 and raw_lines[0] == "":
                    raw_lines = raw_lines[1:]
                if len(raw_lines) > 1 and raw_lines[-1] == "":
                    raw_lines = raw_lines[:-1]
                lines = raw_lines
            else:
                # '.' is used for transparency and ' ' is not in legend:
                # strip outer blank wrapper lines from multiline literals and strip indentation spaces
                while raw_lines and raw_lines[0].strip(" \t") == "":
                    raw_lines.pop(0)
                while raw_lines and raw_lines[-1].strip(" \t") == "":
                    raw_lines.pop()
                lines = [line.strip(" \t") for line in raw_lines]
        else:
            raise ValueError("grid must be a string or list of strings.")

        if self.strict and lines:
            expected_len = len(lines[0])
            for idx, row_str in enumerate(lines):
                if len(row_str) != expected_len:
                    raise ValueError(
                        f"Ragged ASCII grid row at index {idx}: expected width {expected_len}, got {len(row_str)}."
                    )

        self.lines = lines

    def execute(self, document):
        w, h = document.width, document.height
        if self.strict:
            if self.offset_y < 0 or self.offset_y + len(self.lines) > h:
                raise ValueError(
                    f"ASCII grid height ({len(self.lines)} at offset_y={self.offset_y}) exceeds canvas height ({h})."
                )
            for row_str in self.lines:
                if self.offset_x < 0 or self.offset_x + len(row_str) > w:
                    raise ValueError(
                        f"ASCII grid width ({len(row_str)} at offset_x={self.offset_x}) exceeds canvas width ({w})."
                    )

        pixels = document.image.load()
        parsed_legend = {}
        for ch, col in self.legend.items():
            if col in ("transparent", "none", "clear", None):
                parsed_legend[ch] = None
            else:
                parsed_legend[ch] = parse_color_value(col, document.mode, document=document)

        clear_val = 0 if document.mode == "P" else ((0, 0, 0, 0) if document.mode == "RGBA" else (0, 0, 0))

        for row_idx, row_str in enumerate(self.lines):
            y = self.offset_y + row_idx
            if not (0 <= y < h):
                continue
            for col_idx, ch in enumerate(row_str):
                x = self.offset_x + col_idx
                if not (0 <= x < w):
                    continue
                if ch in parsed_legend:
                    val = parsed_legend[ch]
                    if val is None:
                        if self.transparent_behavior == "clear":
                            pixels[x, y] = clear_val
                    else:
                        pixels[x, y] = val
                elif ch in (".", " "):
                    if self.transparent_behavior == "clear":
                        pixels[x, y] = clear_val
                elif self.strict:
                    raise ValueError(f"Character '{ch}' at ({x}, {y}) not found in legend.")


class ApplyShading(Command):
    """
    Applies directional pixel-art highlights and shadows to interior pixels (excluding outline).
    light_dir can be 'top_left', 'top_right', 'top', 'left', 'right'.
    """
    def __init__(self, light_dir: str = "top_left", intensity: float = 0.22):
        self.light_dir = light_dir
        self.intensity = float(intensity)

    def execute(self, document):
        if document.mode == "P":
            raise ValueError("ApplyShading requires RGBA or RGB mode document.")
        w, h = document.width, document.height
        pixels = document.image.load()

        from ..analysis.sprite_analysis import SpriteAnalysis
        analysis = SpriteAnalysis(document.image)
        outline = analysis.outline

        light_vecs = {
            "top_left": (-1, -1),
            "top_right": (1, -1),
            "top": (0, -1),
            "left": (-1, 0),
            "right": (1, 0),
        }
        lx, ly = light_vecs.get(self.light_dir, (-1, -1))

        def is_interior_or_opaque(x, y):
            if 0 <= x < w and 0 <= y < h:
                p = pixels[x, y]
                return (p[3] > 0) if document.mode == "RGBA" else True
            return False

        updates = {}
        for y in range(h):
            for x in range(w):
                if not is_interior_or_opaque(x, y) or (x, y) in outline:
                    continue
                # Check if pixel is on the light-facing edge of the interior (borders outline or transparency in light direction)
                up_x, up_y = x + lx, y + ly
                dn_x, dn_y = x - lx, y - ly
                is_highlight = (not is_interior_or_opaque(up_x, up_y)) or ((up_x, up_y) in outline)
                is_shadow = (not is_interior_or_opaque(dn_x, dn_y)) or ((dn_x, dn_y) in outline)

                p = pixels[x, y]
                r, g, b = p[0], p[1], p[2]
                a = p[3] if len(p) > 3 else 255
                if is_highlight and not is_shadow:
                    # Warm highlight shift
                    nr = min(255, int(r + (255 - r) * self.intensity + 8))
                    ng = min(255, int(g + (255 - g) * self.intensity + 6))
                    nb = min(255, int(b + (255 - b) * (self.intensity * 0.7)))
                    updates[(x, y)] = (nr, ng, nb, a) if document.mode == "RGBA" else (nr, ng, nb)
                elif is_shadow and not is_highlight:
                    # Cool shadow shift
                    nr = max(0, int(r * (1.0 - self.intensity * 1.1)))
                    ng = max(0, int(g * (1.0 - self.intensity)))
                    nb = max(0, int(b * (1.0 - self.intensity * 0.75)))
                    updates[(x, y)] = (nr, ng, nb, a) if document.mode == "RGBA" else (nr, ng, nb)

        for (x, y), col in updates.items():
            pixels[x, y] = col


class ReplaceIndex(Command):
    """Replaces all occurrences of an old index with a new index ('P' mode only)."""
    def __init__(self, old_index, new_index):
        self.old_index = int(old_index)
        self.new_index = int(new_index)

    def execute(self, document):
        if document.mode != 'P':
            raise ValueError("ReplaceIndex requires 'P' mode document.")
        PaletteOperations.replace_index(document.image, self.old_index, self.new_index)


class ReplaceColor(Command):
    """
    Replaces a color (R,G,B) with another.
    In 'P' mode, this modifies the palette entry.
    In 'RGBA'/'RGB' mode, it replaces pixel values.
    """
    def __init__(self, old_color, new_color):
        self.old_color = self._parse_color(old_color)
        self.new_color = self._parse_color(new_color)

    def _parse_color(self, color):
        if isinstance(color, str) and color.startswith('#'):
            color = color.lstrip('#')
            if len(color) == 6:
                return tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
            elif len(color) == 8:
                return tuple(int(color[i:i+2], 16) for i in (0, 2, 4, 6))
        return color

    def execute(self, document):
        PaletteOperations.replace_color(document.image, self.old_color, self.new_color)


class Mirror(Command):
    """Mirrors the image horizontally or vertically."""
    def __init__(self, direction="horizontal"):
        if direction not in ("horizontal", "vertical"):
            raise ValueError("Direction must be 'horizontal' or 'vertical'")
        self.direction = direction

    def execute(self, document):
        import PIL.ImageOps
        from PIL import Image
        method = Image.FLIP_LEFT_RIGHT if self.direction == "horizontal" else Image.FLIP_TOP_BOTTOM

        # PIL transpose preserves palette and mode
        document.image = document.image.transpose(method)


class Crop(Command):
    """Crops the image to a bounding box (left, upper, right, lower)."""
    def __init__(self, left, upper, right, lower):
        self.bbox = (int(left), int(upper), int(right), int(lower))

    def execute(self, document):
        document.image = document.image.crop(self.bbox)


class ResizeCanvas(Command):
    """Resizes canvas without scaling image (anchored top-left)."""
    def __init__(self, width, height, fill_index=0, fill_color=(0,0,0,0)):
        self.width = int(width)
        self.height = int(height)
        self.fill_index = fill_index
        self.fill_color = fill_color

    def execute(self, document):
        new_img = Image.new(document.mode, (self.width, self.height))

        if document.mode == 'P':
            new_img.putpalette(document.image.getpalette())
            if 'transparency' in document.image.info:
                new_img.info['transparency'] = document.image.info['transparency']
            # fill with transparent/default index
            new_img.paste(self.fill_index, (0, 0, self.width, self.height))
        else:
            new_img.paste(self.fill_color, (0, 0, self.width, self.height))

        new_img.paste(document.image, (0, 0))
        document.image = new_img
