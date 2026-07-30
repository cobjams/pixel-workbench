import json
from PIL import Image

def compare_images(old_img, new_img, output_png_path=None):
    """
    Compares two PIL Images.
    Returns a dictionary diff report.
    Optionally saves a visual diff PNG.
    """
    w1, h1 = old_img.size
    w2, h2 = new_img.size

    report = {
        "changed_pixels": 0,
        "bounding_box": None,
        "changed_palette_indices": [],
        "added_colors": [],
        "removed_colors": [],
        "dimensions_changed": (w1, h1) != (w2, h2),
        "validation_passed": True # could integrate validation here later
    }

    w = min(w1, w2)
    h = min(h1, h2)

    min_x, min_y, max_x, max_y = float('inf'), float('inf'), -1, -1

    # We will compute changes via RGBA comparison for simplicity,
    # but we can track palette index changes if both are 'P'.

    if old_img.mode == 'P' and new_img.mode == 'P':
        old_pal = old_img.getpalette()
        new_pal = new_img.getpalette()
        if old_pal and new_pal:
            for i in range(256):
                idx = i * 3
                if old_pal[idx:idx+3] != new_pal[idx:idx+3]:
                    report["changed_palette_indices"].append(i)

    # For visual diff
    if output_png_path:
        diff_vis = Image.new("RGBA", (max(w1, w2), max(h1, h2)), (0, 0, 0, 0))
        # Dim the old image as base
        base_img = old_img.convert("RGBA")
        base_data = base_img.load()
        diff_data = diff_vis.load()

        for y in range(h1):
            for x in range(w1):
                r, g, b, a = base_data[x, y]
                # Make it semi-transparent
                diff_data[x, y] = (r, g, b, int(a * 0.3))

    old_rgb = old_img.convert("RGBA")
    new_rgb = new_img.convert("RGBA")

    old_pixels = old_rgb.load()
    new_pixels = new_rgb.load()

    old_colors = set()
    new_colors = set()

    for y in range(max(h1, h2)):
        for x in range(max(w1, w2)):
            if x < w1 and y < h1:
                old_colors.add(old_pixels[x, y])
            if x < w2 and y < h2:
                new_colors.add(new_pixels[x, y])

            is_diff = False
            if x >= w1 or y >= h1 or x >= w2 or y >= h2:
                is_diff = True
            elif old_pixels[x, y] != new_pixels[x, y]:
                is_diff = True

            if is_diff:
                report["changed_pixels"] += 1
                if x < min_x: min_x = x
                if y < min_y: min_y = y
                if x > max_x: max_x = x
                if y > max_y: max_y = y

                if output_png_path and x < max(w1, w2) and y < max(h1, h2):
                    # Highlight diff in red-ish overlay
                    if x < w2 and y < h2:
                        diff_data[x, y] = (255, 0, 0, 255)
                    else:
                        diff_data[x, y] = (255, 0, 255, 255) # Out of bounds diff

    if report["changed_pixels"] > 0:
        report["bounding_box"] = [min_x, min_y, max_x, max_y]

    report["added_colors"] = [f"#{r:02x}{g:02x}{b:02x}{a:02x}" for r, g, b, a in (new_colors - old_colors)]
    report["removed_colors"] = [f"#{r:02x}{g:02x}{b:02x}{a:02x}" for r, g, b, a in (old_colors - new_colors)]

    if output_png_path:
        diff_vis.save(output_png_path)

    return report

def compare_files(old_path, new_path, output_png_path=None, output_json_path=None):
    old_img = Image.open(old_path)
    new_img = Image.open(new_path)

    report = compare_images(old_img, new_img, output_png_path)

    if output_json_path:
        with open(output_json_path, 'w') as f:
            json.dump(report, f, indent=2)

    return report
