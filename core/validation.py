from collections import defaultdict
from .palette import PaletteOperations

class ValidationResult:
    def __init__(self):
        self.ok = True
        self.errors = []
        self.warnings = []

    def add_error(self, msg):
        self.ok = False
        self.errors.append(msg)

    def add_warning(self, msg):
        self.warnings.append(msg)

    def to_dict(self):
        return {
            "ok": self.ok,
            "errors": self.errors,
            "warnings": self.warnings
        }


def validate_document(document, expected_dimensions=None):
    """
    Validates a Document for incorrect dimensions, duplicate colors,
    unused colors, palette overflows, and fully transparent edges.
    """
    result = ValidationResult()
    if not document.image:
        result.add_error("No image loaded.")
        return result

    img = document.image
    w, h = img.size

    # 1. Dimensions
    if expected_dimensions and (w, h) != expected_dimensions:
        result.add_error(f"Incorrect dimensions: expected {expected_dimensions}, got {(w, h)}")

    # 2. Transparent Rows/Columns (Warnings)
    if 'transparency' in img.info or img.mode == 'RGBA':
        trans_val = img.info.get('transparency')

        def is_pixel_transparent(x, y):
            val = img.getpixel((x, y))
            if img.mode == 'P':
                return val == trans_val
            elif img.mode == 'RGBA':
                return val[3] == 0
            return False

        # Check top row
        if all(is_pixel_transparent(x, 0) for x in range(w)):
            result.add_warning("Fully transparent top row detected.")
        # Check bottom row
        if all(is_pixel_transparent(x, h-1) for x in range(w)):
            result.add_warning("Fully transparent bottom row detected.")
        # Check left col
        if all(is_pixel_transparent(0, y) for y in range(h)):
            result.add_warning("Fully transparent left column detected.")
        # Check right col
        if all(is_pixel_transparent(w-1, y) for y in range(h)):
            result.add_warning("Fully transparent right column detected.")

    # 3. Palette Validation
    if img.mode == 'P':
        colors = PaletteOperations.get_palette_colors(img)

        # Check for duplicates
        seen = set()
        duplicates = set()
        # Find which indices are actually used
        used_indices = set()
        for y in range(h):
            for x in range(w):
                used_indices.add(img.getpixel((x, y)))

        # Some images have a 256 color palette but only use first N
        # We only care about duplicates among the *used* portion or up to the max index
        max_used_index = max(used_indices) if used_indices else 0

        for i in range(max_used_index + 1):
            if i < len(colors):
                c = colors[i]
                if c in seen:
                    # Ignore duplicate (0,0,0) if it's padding
                    if c != (0,0,0) or i in used_indices:
                        duplicates.add(c)
                seen.add(c)

        if duplicates:
            result.add_warning(f"Duplicate colors found in palette: {duplicates}")

        # Check unused colors (only warning for indices < max_used_index to ignore padding)
        unused = []
        for i in range(max_used_index + 1):
            if i not in used_indices:
                unused.append(i)
        if unused:
            result.add_warning(f"Unused palette indices found before max index: {unused}")

        # Palette overflow (if pixels use indices >= 256)
        if max_used_index >= 256:
            result.add_error(f"Palette overflow: pixel index {max_used_index} exceeds 255.")

    return result
