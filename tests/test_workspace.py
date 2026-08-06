import unittest
from PIL import Image

from pixel_workbench.core.document import Document
from pixel_workbench.analysis.workspace import SpriteWorkspace
from pixel_workbench.analysis.adapters.agent import CodingAgentProvider

class TestSpriteWorkspace(unittest.TestCase):
    def setUp(self):
        self.doc = Document()
        # Create a 4x4 image
        self.doc.image = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
        self.doc.original_mode = "RGBA"
        self.doc.push_state()

    def test_workspace_initialization(self):
        """Test that a SpriteWorkspace successfully bundles Document and Analysis."""
        ws = SpriteWorkspace(
            document=self.doc,
            constraints={"required_size": (4, 4)},
            project_metadata={"theme": "test"}
        )

        self.assertIsNotNone(ws.document)
        self.assertIsNotNone(ws.analysis)
        self.assertIsNotNone(ws.validation)
        self.assertEqual(ws.constraints["required_size"], (4, 4))
        self.assertEqual(ws.project_metadata["theme"], "test")

        # Verify commands are populated
        self.assertIn("paint_color", ws.commands)
        self.assertIn("repair", ws.commands)

    def test_workspace_refresh(self):
        """Test that refresh() correctly updates analysis after a mutation."""
        ws = SpriteWorkspace(self.doc)

        # Initially, image is blank (0 connected components, or empty ones)
        initial_components = len(ws.analysis.connected_components)

        # Mutate the document using a command from the workspace
        ws.commands["paint_color"](0, 0, (255, 0, 0, 255))

        # State should be stale until refresh
        self.assertEqual(len(ws.analysis.connected_components), initial_components)

        # Refresh the workspace
        ws.refresh()

        # Now the analysis should reflect the newly added component
        self.assertNotEqual(len(ws.analysis.connected_components), initial_components)
        self.assertEqual(len(ws.analysis.connected_components), 1)

    def test_coding_agent_provider_returns_workspace(self):
        """Test that the CodingAgentProvider returns a well-formed SpriteWorkspace."""
        provider = CodingAgentProvider()

        workspace = provider.generate_sprite(prompt="test prompt", size=(16, 16))

        self.assertIsInstance(workspace, SpriteWorkspace)
        self.assertEqual(workspace.document.width, 16)
        self.assertEqual(workspace.document.height, 16)
        self.assertTrue(workspace.constraints["must_have_transparent_background"])

if __name__ == "__main__":
    unittest.main()
