from typing import Dict, Any, List, Optional, Set, Tuple, Union
from PIL import Image

from ..core.document import Document
from ..core.commands import ApplyAsciiGrid
from ..tools.compare import compare_images
from .sprite_analysis import SpriteAnalysis
from .repair.engine import RepairEngine
from .repair.rules import RemoveJaggiesRule


def _to_document(obj: Union[Document, Image.Image, str]) -> Document:
    if isinstance(obj, Document):
        return obj
    doc = Document()
    if isinstance(obj, str):
        doc.load(obj)
    elif isinstance(obj, Image.Image):
        doc.image = obj.copy()
        doc.original_mode = obj.mode
    else:
        raise ValueError(f"Unsupported sprite target type: {type(obj)}")
    return doc


def check_grid_roundtrip(target: Union[Document, Image.Image, str]) -> Dict[str, Any]:
    """
    QA Test 1: Grid Round-Trip
    Verifies that Image -> ASCII Grid -> Image produces the exact same pixels,
    including transparency and alpha values.
    """
    doc = _to_document(target)
    if not doc.image:
        return {"passed": False, "error": "Document contains no image."}

    orig_rgba = doc.image.convert("RGBA")
    w, h = orig_rgba.size
    analysis = SpriteAnalysis(orig_rgba)
    grid_data = analysis.to_ascii_grid(include_legend=True)

    reconstructed_doc = Document()
    reconstructed_doc.image = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    reconstructed_doc.original_mode = "RGBA"

    cmd = ApplyAsciiGrid(
        grid=grid_data["grid"],
        legend=grid_data["legend"],
        offset_x=0,
        offset_y=0,
        transparent_behavior="clear",
        preserve_whitespace=True,
        strict=True,
    )
    cmd.execute(reconstructed_doc)

    diff = compare_images(orig_rgba, reconstructed_doc.image)
    passed = diff["changed_pixels"] == 0 and not diff["dimensions_changed"]
    return {
        "test": "grid_roundtrip",
        "passed": passed,
        "changed_pixels": diff["changed_pixels"],
        "bounding_box": diff["bounding_box"],
    }


def check_palette_regression(
    before: Union[Document, Image.Image, str],
    after: Union[Document, Image.Image, str],
    allowed_colors: Optional[List[str]] = None,
    max_colors: Optional[int] = None,
    allow_new_colors: bool = False
) -> Dict[str, Any]:
    """
    QA Test 2: Palette Regression
    Verifies that no unexpected colors were introduced and palette limits are respected.
    """
    before_doc = _to_document(before)
    after_doc = _to_document(after)
    before_analysis = SpriteAnalysis(before_doc.image)
    after_analysis = SpriteAnalysis(after_doc.image)

    before_hex = set(before_analysis.to_dict(include_grid=False)["palette"])
    after_hex = set(after_analysis.to_dict(include_grid=False)["palette"])

    baseline = {c.lower() for c in allowed_colors} if allowed_colors is not None else before_hex
    unexpected_colors = sorted(after_hex - baseline) if not allow_new_colors else []

    max_exceeded = False
    if max_colors is not None and len(after_hex) > max_colors:
        max_exceeded = True

    passed = (len(unexpected_colors) == 0) and (not max_exceeded)
    return {
        "test": "palette_regression",
        "passed": passed,
        "before_palette_count": len(before_hex),
        "after_palette_count": len(after_hex),
        "unexpected_colors": unexpected_colors,
        "removed_colors": sorted(before_hex - after_hex),
        "max_colors_exceeded": max_exceeded,
    }


def check_outline_regression(
    before: Union[Document, Image.Image, str],
    after: Union[Document, Image.Image, str],
    expected_outline_color: Optional[str] = None
) -> Dict[str, Any]:
    """
    QA Test 3: Outline Regression
    Verifies that no broken or inconsistent outlines were introduced compared to baseline.
    Specifically checks if interior colors leaked onto the outer boundary where a closed
    outline previously existed.
    """
    before_doc = _to_document(before)
    after_doc = _to_document(after)

    before_rgba = before_doc.image.convert("RGBA")
    after_rgba = after_doc.image.convert("RGBA")
    before_analysis = SpriteAnalysis(before_rgba)
    after_analysis = SpriteAnalysis(after_rgba)

    b_px = before_rgba.load()
    a_px = after_rgba.load()

    def _to_hex(rgba):
        return f"#{rgba[0]:02x}{rgba[1]:02x}{rgba[2]:02x}"

    before_outline_colors = {_to_hex(b_px[x, y]) for x, y in before_analysis.outline if b_px[x, y][3] > 0}
    after_outline_colors = {_to_hex(a_px[x, y]) for x, y in after_analysis.outline if a_px[x, y][3] > 0}

    # Check if interior colors from 'after' that were NOT on 'before' outline are now exposed on 'after' outline
    leaked_coords = []
    if expected_outline_color:
        target_hex = expected_outline_color.lower()
        for x, y in sorted(after_analysis.outline):
            if a_px[x, y][3] > 0 and _to_hex(a_px[x, y]) != target_hex:
                leaked_coords.append([x, y])
    elif len(before_outline_colors) == 1 and len(before_analysis.outline) > 0:
        # Baseline had a strict single-color closed outline
        dom_outline_hex = next(iter(before_outline_colors))
        for x, y in sorted(after_analysis.outline):
            if a_px[x, y][3] > 0 and _to_hex(a_px[x, y]) != dom_outline_hex:
                leaked_coords.append([x, y])

    jaggies_rule = RemoveJaggiesRule()
    before_jaggies = len(jaggies_rule._find_corner_doubles(before_doc, before_analysis))
    after_jaggies = len(jaggies_rule._find_corner_doubles(after_doc, after_analysis))

    passed = (len(leaked_coords) == 0) and (len(after_analysis.outline) > 0 or len(before_analysis.outline) == 0)
    return {
        "test": "outline_regression",
        "passed": passed,
        "before_outline_colors": sorted(before_outline_colors),
        "after_outline_colors": sorted(after_outline_colors),
        "outline_leaks": leaked_coords,
        "jaggies_before": before_jaggies,
        "jaggies_after": after_jaggies,
    }


def check_symmetry_validation(
    before: Union[Document, Image.Image, str],
    after: Union[Document, Image.Image, str],
    min_horizontal: Optional[float] = None,
    min_vertical: Optional[float] = None,
    preserve_baseline: bool = True
) -> Dict[str, Any]:
    """
    QA Test 4: Symmetry Validation
    Verifies that intended horizontal/vertical symmetry is preserved.
    """
    before_doc = _to_document(before)
    after_doc = _to_document(after)
    before_sym = SpriteAnalysis(before_doc.image).symmetry
    after_sym = SpriteAnalysis(after_doc.image).symmetry

    target_h = min_horizontal if min_horizontal is not None else (before_sym["horizontal"] if preserve_baseline else 0.0)
    target_v = min_vertical if min_vertical is not None else (before_sym["vertical"] if preserve_baseline else 0.0)

    # Find specific asymmetric coordinate pairs horizontally
    rgba = after_doc.image.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size
    asymmetric_pairs = []
    for y in range(h):
        for x in range(w // 2):
            mx = w - 1 - x
            if (px[x, y][3] > 0 or px[mx, y][3] > 0) and px[x, y] != px[mx, y]:
                asymmetric_pairs.append([[x, y], [mx, y]])

    passed = (after_sym["horizontal"] >= target_h) and (after_sym["vertical"] >= target_v)
    return {
        "test": "symmetry_validation",
        "passed": passed,
        "before_symmetry": before_sym,
        "after_symmetry": after_sym,
        "required_horizontal": target_h,
        "required_vertical": target_v,
        "horizontal_asymmetric_pairs": asymmetric_pairs[:16],
    }


def check_animation_regression(
    frames: List[Union[Document, Image.Image, str]],
    max_com_shift: float = 4.0,
    max_volume_delta_ratio: float = 0.35
) -> Dict[str, Any]:
    """
    QA Test 5: Animation Regression
    Verifies consistency across animation frames: identical dimensions, consistent palette,
    bounded center-of-mass shift, and consistent opaque pixel volume.
    """
    if not frames:
        return {"test": "animation_regression", "passed": False, "error": "No frames provided."}

    docs = [_to_document(f) for f in frames]
    sizes = [d.size for d in docs]
    consistent_dimensions = len(set(sizes)) == 1

    palettes = []
    volumes = []
    centers = []

    for d in docs:
        rgba = d.image.convert("RGBA")
        w, h = rgba.size
        px = rgba.load()
        analysis = SpriteAnalysis(rgba)
        palettes.append(set(analysis.to_dict(include_grid=False)["palette"]))

        opaque_pts = [(x, y) for y in range(h) for x in range(w) if px[x, y][3] > 0]
        volumes.append(len(opaque_pts))
        if opaque_pts:
            cx = sum(p[0] for p in opaque_pts) / len(opaque_pts)
            cy = sum(p[1] for p in opaque_pts) / len(opaque_pts)
            centers.append((round(cx, 2), round(cy, 2)))
        else:
            centers.append((w / 2.0, h / 2.0))

    base_palette = palettes[0]
    palette_drifts = [sorted(pal - base_palette) for pal in palettes[1:] if (pal - base_palette)]

    max_observed_shift = 0.0
    for i in range(len(centers) - 1):
        c1, c2 = centers[i], centers[i + 1]
        dist = ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2) ** 0.5
        if dist > max_observed_shift:
            max_observed_shift = round(dist, 2)

    base_vol = max(1, volumes[0])
    max_vol_delta = max((abs(v - volumes[0]) / base_vol for v in volumes), default=0.0)

    passed = (
        consistent_dimensions
        and len(palette_drifts) == 0
        and max_observed_shift <= max_com_shift
        and max_vol_delta <= max_volume_delta_ratio
    )
    return {
        "test": "animation_regression",
        "passed": passed,
        "frame_count": len(docs),
        "consistent_dimensions": consistent_dimensions,
        "palette_drifts": palette_drifts,
        "frame_volumes": volumes,
        "centers_of_mass": [list(c) for c in centers],
        "max_center_of_mass_shift": max_observed_shift,
        "max_volume_delta_ratio": round(max_vol_delta, 3),
    }


def check_repair_regression(
    target: Union[Document, Image.Image, str],
    protect_coords: Optional[Set[Tuple[int, int]]] = None
) -> Dict[str, Any]:
    """
    QA Test 6: Repair Regression
    Verifies that running safe RepairEngine on a sprite does not damage valid details:
      - Interior 1px color clusters (eyes, highlights)
      - Explicitly protected coordinates
      - Intentional multi-pixel outline accents or symmetric particles
    """
    doc = _to_document(target)
    before_rgba = doc.image.convert("RGBA")
    before_analysis = SpriteAnalysis(before_rgba)

    # Identify all 1px interior color clusters (e.g. eyes, specular highlights)
    interior_detail_coords: Set[Tuple[int, int]] = set()
    for cluster in before_analysis.clusters:
        if cluster["size"] == 1 and cluster["is_interior_detail"]:
            interior_detail_coords.update(cluster["pixels"])

    test_doc = Document()
    test_doc.image = before_rgba.copy()
    test_doc.original_mode = "RGBA"

    engine = RepairEngine(safe=True, protect_coords=protect_coords)
    report = engine.run(test_doc, dry_run=False)

    after_px = test_doc.image.load()
    before_px = before_rgba.load()

    damaged_interior = [
        [x, y]
        for x, y in sorted(interior_detail_coords)
        if after_px[x, y] != before_px[x, y]
    ]
    damaged_protected = [
        [x, y]
        for x, y in sorted(protect_coords or set())
        if after_px[x, y] != before_px[x, y]
    ]

    passed = len(damaged_interior) == 0 and len(damaged_protected) == 0
    return {
        "test": "repair_regression",
        "passed": passed,
        "interior_details_checked": len(interior_detail_coords),
        "damaged_interior_details": damaged_interior,
        "damaged_protected_coords": damaged_protected,
        "preserved_details": report["preserved_details"],
        "repair_actions": report["actions"],
    }


def generate_regression_report(
    before: Union[Document, Image.Image, str],
    after: Union[Document, Image.Image, str],
    constraints: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generates a comprehensive semantic visual regression report comparing 'before' and 'after',
    including pixel diffs, semantic deltas, affected regions, and the pixel-art QA suite.
    """
    constraints = constraints or {}
    before_doc = _to_document(before)
    after_doc = _to_document(after)

    before_rgba = before_doc.image.convert("RGBA")
    after_rgba = after_doc.image.convert("RGBA")

    pixel_diff = compare_images(before_rgba, after_rgba)
    total_pixels = max(1, max(before_rgba.width, after_rgba.width) * max(before_rgba.height, after_rgba.height))
    pixel_diff["similarity_score"] = round(max(0.0, 1.0 - (pixel_diff["changed_pixels"] / total_pixels)), 4)

    before_analysis = SpriteAnalysis(before_rgba)
    after_analysis = SpriteAnalysis(after_rgba)

    # Identify changed coordinates and which semantic regions were modified
    w = min(before_rgba.width, after_rgba.width)
    h = min(before_rgba.height, after_rgba.height)
    b_px = before_rgba.load()
    a_px = after_rgba.load()
    changed_coords = {
        (x, y)
        for y in range(h)
        for x in range(w)
        if b_px[x, y] != a_px[x, y]
    }

    affected_regions = []
    combined_regions = set(before_analysis.semantic_regions.keys()) | set(after_analysis.semantic_regions.keys())
    for reg_name in sorted(combined_regions):
        reg_coords = before_analysis.get_region(reg_name) | after_analysis.get_region(reg_name)
        if changed_coords & reg_coords:
            affected_regions.append(reg_name)

    grid_rt = check_grid_roundtrip(after_doc)
    pal_reg = check_palette_regression(
        before_doc,
        after_doc,
        allowed_colors=constraints.get("allowed_palette"),
        max_colors=constraints.get("max_colors"),
        allow_new_colors=constraints.get("allow_new_colors", True),
    )
    out_reg = check_outline_regression(
        before_doc,
        after_doc,
        expected_outline_color=constraints.get("expected_outline_color"),
    )
    sym_reg = check_symmetry_validation(
        before_doc,
        after_doc,
        min_horizontal=constraints.get("min_horizontal_symmetry"),
        min_vertical=constraints.get("min_vertical_symmetry"),
        preserve_baseline=constraints.get("preserve_symmetry", False),
    )
    rep_reg = check_repair_regression(after_doc)

    tests = {
        "grid_roundtrip": grid_rt,
        "palette_regression": pal_reg,
        "outline_regression": out_reg,
        "symmetry_validation": sym_reg,
        "repair_regression": rep_reg,
    }
    all_passed = all(t["passed"] for t in tests.values())

    return {
        "passed": all_passed,
        "pixel_diff": pixel_diff,
        "semantic_delta": {
            "symmetry_before": before_analysis.symmetry,
            "symmetry_after": after_analysis.symmetry,
            "symmetry_delta": {
                "horizontal": round(after_analysis.symmetry["horizontal"] - before_analysis.symmetry["horizontal"], 2),
                "vertical": round(after_analysis.symmetry["vertical"] - before_analysis.symmetry["vertical"], 2),
            },
            "palette_count_before": len(before_analysis.palette),
            "palette_count_after": len(after_analysis.palette),
            "component_count_before": len(before_analysis.connected_components),
            "component_count_after": len(after_analysis.connected_components),
            "outline_count_before": len(before_analysis.outline),
            "outline_count_after": len(after_analysis.outline),
            "affected_regions": affected_regions,
        },
        "qa_suite": {
            "passed": all_passed,
            "tests": tests,
        },
    }
