import colorsys
from typing import Dict, Set, Tuple, Any

def extract_semantic_regions(analysis: Any) -> Dict[str, Set[Tuple[int, int]]]:
    """
    Extracts semantic regions from a SpriteAnalysis object.
    Regions: 'head', 'body', 'shadow', 'highlight', 'outline'
    """
    regions = {
        "head": set(),
        "body": set(),
        "shadow": set(),
        "highlight": set(),
        "outline": set(),
    }

    width = analysis._width
    height = analysis._height

    color_to_pixels = {}

    for y in range(height):
        for x in range(width):
            pixel = analysis._pixels[x, y]
            if pixel[3] > 0:
                local_y = y % 15
                if local_y < 8:
                    regions["head"].add((x, y))
                else:
                    regions["body"].add((x, y))

                rgb = pixel[:3]
                if rgb not in color_to_pixels:
                    color_to_pixels[rgb] = set()
                color_to_pixels[rgb].add((x, y))

    hue_groups = {}
    for r, g, b in color_to_pixels.keys():
        h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        h_key = round(h, 3)
        if h_key not in hue_groups:
            hue_groups[h_key] = []
        hue_groups[h_key].append((l, (r, g, b)))

    for h_key, colors in hue_groups.items():
        if len(colors) > 1:
            colors.sort(key=lambda x: x[0])
            darkest_l = colors[0][0]
            brightest_l = colors[-1][0]

            if darkest_l < brightest_l:
                for l, rgb in colors:
                    if l == darkest_l:
                        regions["shadow"].update(color_to_pixels[rgb])
                    elif l == brightest_l:
                        regions["highlight"].update(color_to_pixels[rgb])

    regions["outline"] = set(analysis.outline)

    return regions
