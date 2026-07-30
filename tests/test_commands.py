import os
from PIL import Image
from pixel_workbench.core.document import Document
from pixel_workbench.core.commands import PaintIndex, PaintColor, ReplaceIndex, ReplaceColor, Mirror, Crop

def test_commands():
    # Setup test doc in P mode
    doc = Document()
    doc.image = Image.new("P", (10, 10))
    doc.image.putpalette([255, 0, 0, 0, 255, 0, 0, 0, 255] + [0]*759)
    doc.original_mode = 'P'

    # PaintIndex
    cmd = PaintIndex(0, 0, 1)
    cmd.execute(doc)
    assert doc.image.getpixel((0,0)) == 1

    # ReplaceIndex
    cmd = ReplaceIndex(1, 2)
    cmd.execute(doc)
    assert doc.image.getpixel((0,0)) == 2

    # ReplaceColor (palette modify)
    cmd = ReplaceColor((0, 255, 0), (255, 255, 0))
    cmd.execute(doc)
    pal = doc.image.getpalette()
    assert pal[3:6] == [255, 255, 0]

    # Mirror
    doc.image.putpixel((9, 0), 1) # put old green (now yellow) on right
    cmd = Mirror("horizontal")
    cmd.execute(doc)
    assert doc.image.getpixel((0,0)) == 1

    # Crop
    cmd = Crop(0, 0, 5, 5)
    cmd.execute(doc)
    assert doc.image.size == (5, 5)

    print("Command tests passed!")

test_commands()
