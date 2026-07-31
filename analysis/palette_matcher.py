from typing import Tuple, List, Union
from PIL import Image

def extract_palette(image: Image.Image) -> List[Tuple[int, int, int]]:
    """Extracts a list of RGB colors from an image."""
    if image.mode == 'P':
        palette = image.getpalette()
        if palette:
            # Only extract unique colors up to the actual number used,
            # or just filter out trailing zero padding if it's unused.
            # A more robust way is to check the image's getcolors() for 'P' mode, but
            # for a flat palette we can just remove duplicates and trailing (0,0,0)s
            # if they are just padding. However, we'll just extract what's actually in the image
            # to be safe and accurate.
            colors_used = image.getcolors()
            if colors_used:
                used_indices = [c[1] for c in colors_used]
                return [(palette[i*3], palette[i*3+1], palette[i*3+2]) for i in used_indices]

    # If not P mode, or palette is missing, extract unique colors
    rgba_img = image.convert("RGBA")
    unique_colors = set()
    for p in rgba_img.getdata():
        if p[3] > 0:  # Ignore fully transparent pixels
            unique_colors.add((p[0], p[1], p[2]))
    return list(unique_colors)

def match_palette(image: Image.Image, reference_palette: Union[str, Image.Image, List[Tuple[int, int, int]]]) -> List[Tuple[int, int, int]]:
    """
    Returns the target palette to match.
    The reference_palette can be a filepath, an Image object, or a list of RGB tuples.
    """
    if isinstance(reference_palette, str):
        with Image.open(reference_palette) as ref_img:
            return extract_palette(ref_img)
    elif isinstance(reference_palette, Image.Image):
        return extract_palette(reference_palette)
    elif isinstance(reference_palette, list):
        return reference_palette
    else:
        raise ValueError("Invalid reference_palette type.")

def quantize_to_palette(image: Image.Image, palette_colors: List[Tuple[int, int, int]]) -> Image.Image:
    """
    Quantizes an image to the nearest colors in the provided palette_colors.
    Returns a new 'P' mode Image.
    """
    if not palette_colors:
        return image.copy()

    # Create a flat list for the PIL palette (max 256 colors)
    flat_palette = []
    for r, g, b in palette_colors[:256]:
        flat_palette.extend([r, g, b])

    # Pad to 256 colors
    flat_palette.extend([0] * (768 - len(flat_palette)))

    # Create a dummy image to hold the palette
    pal_img = Image.new('P', (1, 1))
    pal_img.putpalette(flat_palette)

    # Convert original to RGB (dropping alpha temporarily for standard quantize,
    # though in a real app we'd handle alpha carefully)
    rgb_img = image.convert("RGB")

    # Quantize
    quantized_img = rgb_img.quantize(palette=pal_img, dither=Image.Dither.NONE)

    # Handle transparency restoration (simplified for v1)
    if image.mode in ('RGBA', 'LA') or (image.mode == 'P' and 'transparency' in image.info):
        rgba_img = image.convert("RGBA")
        q_rgba = quantized_img.convert("RGBA")

        # We need to manually apply the alpha mask back
        # This is a bit of a hack for v1, ideally we use proper indexed transparency
        for y in range(rgba_img.height):
            for x in range(rgba_img.width):
                r, g, b, a = rgba_img.getpixel((x, y))
                if a == 0:
                    # Set transparent pixels to index 0 (assuming 0 is transparent)
                    # In a true P mode with transparency, this requires more care
                    pass

        # For simplicity in the plugin stub, we return the quantized P image
        # Further refinement needed for robust alpha handling in P mode
        pass

    return quantized_img
