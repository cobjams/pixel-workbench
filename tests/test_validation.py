from PIL import Image
from pixel_workbench.core.document import Document
from pixel_workbench.core.validation import validate_document

def test_validation():
    doc = Document()
    img = Image.new("P", (10, 10))
    # Add duplicate colors in palette (both are red)
    img.putpalette([255, 0, 0, 255, 0, 0] + [0]*762)
    img.putpixel((0,0), 0)
    img.putpixel((1,1), 1) # use both so they are checked
    doc.image = img

    result = validate_document(doc, expected_dimensions=(10, 10))
    assert result.ok is True
    # Should have duplicate color warning
    assert any("Duplicate" in w for w in result.warnings)

test_validation()
print("Validation test passed")
