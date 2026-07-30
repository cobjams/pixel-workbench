from PIL import Image
from .history import HistoryStack

class Document:
    def __init__(self):
        self.image = None
        self.history = HistoryStack()
        self.metadata = {}
        self.filepath = None
        self.original_mode = None

    def load(self, filepath):
        """Loads an image from a file, creating the initial history state."""
        self.filepath = filepath
        img = Image.open(filepath)

        # We always want a memory-independent copy of the loaded file
        # and to preserve transparency info.
        self.image = img.copy()

        # Save info like transparency index if it's there
        if 'transparency' in img.info:
            self.image.info['transparency'] = img.info['transparency']

        self.original_mode = self.image.mode
        self.metadata = {'filepath': filepath}

        # Initialize history but do NOT push the first loaded state as an undoable action.
        # Undo means "undo to previous edit", not "undo loading the file".
        # We start with empty history for a fresh file.
        self.history = HistoryStack()

    def save(self, filepath=None):
        """Saves the current image to a file."""
        if filepath is None:
            filepath = self.filepath

        if not filepath:
            raise ValueError("No filepath specified for saving.")

        self.image.save(filepath)
        self.filepath = filepath

    def push_state(self, action_name=None):
        """
        Manually push the current state to history.
        Should be called BEFORE modifying the image, so we can undo TO this state.
        """
        if self.image:
            meta = {'action': action_name} if action_name else {}
            self.history.push(self.image, meta)

    def undo(self):
        """Undoes the last action, restoring the previous image state."""
        if not self.history.can_undo():
            return False

        result = self.history.undo(self.image, self.metadata)
        if result:
            self.image, self.metadata = result
            return True
        return False

    def redo(self):
        """Redoes the last undone action."""
        if not self.history.can_redo():
            return False

        result = self.history.redo(self.image, self.metadata)
        if result:
            self.image, self.metadata = result
            return True
        return False

    @property
    def mode(self):
        return self.image.mode if self.image else None

    @property
    def size(self):
        return self.image.size if self.image else (0, 0)

    @property
    def width(self):
        return self.size[0]

    @property
    def height(self):
        return self.size[1]
