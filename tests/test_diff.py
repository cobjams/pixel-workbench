import os
from PIL import Image
from pixel_workbench.tools.compare import compare_images

def test_diff():
    img1 = Image.new("RGB", (10, 10), (0, 0, 0))
    img2 = Image.new("RGB", (10, 10), (0, 0, 0))
    img2.putpixel((5, 5), (255, 0, 0))

    report = compare_images(img1, img2, "test_diff_out.png")

    assert report["changed_pixels"] == 1
    assert report["bounding_box"] == [5, 5, 5, 5]
    assert len(report["added_colors"]) == 1
    assert os.path.exists("test_diff_out.png")
    os.remove("test_diff_out.png")

test_diff()
print("Diff test passed")
