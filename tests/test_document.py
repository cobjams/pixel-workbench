import os
from PIL import Image
from pixel_workbench.core.document import Document

def test_document_load_save_history():
    doc = Document()

    # Create test image
    img = Image.new("P", (10, 10))
    img.putpalette([255, 0, 0, 0, 255, 0, 0, 0, 255] + [0]*759)
    img.putpixel((0,0), 0) # red
    img.save("test.png")

    doc.load("test.png")
    assert doc.mode == "P"
    assert doc.image.getpixel((0,0)) == 0

    # modify
    doc.push_state("paint")
    doc.image.putpixel((0,0), 1) # green
    assert doc.image.getpixel((0,0)) == 1

    # undo
    assert doc.undo() is True
    assert doc.image.getpixel((0,0)) == 0

    # redo
    assert doc.redo() is True
    assert doc.image.getpixel((0,0)) == 1

    os.remove("test.png")

test_document_load_save_history()
print("Tests passed")
