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

    def slice_frames(self, frame_width: int, frame_height: int):
        """
        Slices the current document image (left-to-right, top-to-bottom)
        into a list of frame Document objects of size (frame_width, frame_height).
        """
        if not self.image:
            return []
        w, h = self.image.size
        frames = []
        for y in range(0, h, frame_height):
            for x in range(0, w, frame_width):
                if x + frame_width <= w and y + frame_height <= h:
                    frame_doc = Document()
                    frame_doc.image = self.image.crop((x, y, x + frame_width, y + frame_height))
                    frame_doc.original_mode = self.original_mode or self.image.mode
                    if "transparency" in self.image.info:
                        frame_doc.image.info["transparency"] = self.image.info["transparency"]
                    frames.append(frame_doc)
        return frames

    @staticmethod
    def assemble_sprite_sheet(frames, columns: int = None) -> "Document":
        """
        Assembles a list of Document or PIL.Image frames into a single horizontal or grid sprite sheet Document.
        """
        if not frames:
            raise ValueError("Cannot assemble an empty frame list.")
        pil_frames = [f.image if isinstance(f, Document) else f for f in frames]
        fw, fh = pil_frames[0].size
        cols = columns or len(pil_frames)
        rows = (len(pil_frames) + cols - 1) // cols
        mode = pil_frames[0].mode
        bg = 0 if mode == "P" else ((0, 0, 0, 0) if mode == "RGBA" else (0, 0, 0))
        sheet_img = Image.new(mode, (fw * cols, fh * rows), bg)
        if mode == "P" and pil_frames[0].getpalette():
            sheet_img.putpalette(pil_frames[0].getpalette())
        if "transparency" in pil_frames[0].info:
            sheet_img.info["transparency"] = pil_frames[0].info["transparency"]

        for idx, frame_img in enumerate(pil_frames):
            r = idx // cols
            c = idx % cols
            sheet_img.paste(frame_img, (c * fw, r * fh))

        sheet_doc = Document()
        sheet_doc.image = sheet_img
        sheet_doc.original_mode = mode
        return sheet_doc

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
