from PIL import Image
from .palette import PaletteOperations

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
            document.image.putpixel((self.x, self.y), self.color)


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
