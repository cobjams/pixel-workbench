import os
from collections import Counter
from typing import Dict, Any
from PIL import Image

def analyze_style(path: str) -> Dict[str, Any]:
    """
    Analyzes images in a directory (or a single file) and returns structured
    style metrics such as average sizes, color palette distribution, etc.
    """
    files_to_process = []

    if os.path.isfile(path):
        files_to_process.append(path)
    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            for file in files:
                if file.lower().endswith(('.png', '.bmp', '.gif')):
                    files_to_process.append(os.path.join(root, file))

    sprite_count = 0
    size_counter = Counter()
    palette_sizes = []
    transparency_pixels = 0
    total_pixels = 0
    all_colors = Counter()

    for file in files_to_process:
        try:
            with Image.open(file) as img:
                sprite_count += 1
                size_counter[img.size] += 1

                # Convert to RGBA to standardise analysis
                rgba_img = img.convert("RGBA")
                width, height = rgba_img.size

                img_total_pixels = width * height
                total_pixels += img_total_pixels

                unique_colors = set()

                pixels = rgba_img.getdata()
                for pixel in pixels:
                    if len(pixel) >= 4 and pixel[3] == 0:  # fully transparent
                        transparency_pixels += 1
                    else:
                        unique_colors.add(pixel)
                        all_colors[pixel] += 1

                palette_sizes.append(len(unique_colors))
        except Exception:
            # Skip unreadable files silently for now
            continue

    if sprite_count == 0:
        return {"error": f"No valid images found in {path}"}

    common_sizes = [list(size) for size, _ in size_counter.most_common(5)]
    avg_palette_size = sum(palette_sizes) / len(palette_sizes) if palette_sizes else 0
    transparency_percentage = (transparency_pixels / total_pixels * 100) if total_pixels > 0 else 0

    # Get top 5 most common colors (format as hex)
    def rgba_to_hex(r, g, b, a):
        return f"#{r:02x}{g:02x}{b:02x}"

    most_common_colors = [
        rgba_to_hex(*color) for color, _ in all_colors.most_common(5)
    ]

    # For v1, returning a simple dictionary matching the requested schema layout
    return {
        "sprite_count": sprite_count,
        "common_sizes": common_sizes,
        "average_palette_size": round(avg_palette_size, 2),
        "most_common_colors": most_common_colors,
        "transparency_percentage": round(transparency_percentage, 2),
        # Placeholder for more complex metrics to be implemented later
        "outline_color": most_common_colors[-1] if most_common_colors else "#000000",
        "lighting_direction": "unknown",
        "average_contrast": 0.5,
        "outline_percentage": 0.0,
        "cluster_statistics": {}
    }
