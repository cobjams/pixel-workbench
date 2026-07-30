class HistoryEntry:
    def __init__(self, image, metadata=None):
        """
        Takes a full snapshot of the PIL Image and metadata.
        For indexed mode 'P', image.copy() also clones the palette.
        """
        self.image = image.copy()
        self.metadata = metadata or {}


class HistoryStack:
    def __init__(self):
        self._undo_stack = []
        self._redo_stack = []

    def push(self, image, metadata=None):
        """
        Pushes a new state onto the history stack.
        Clears the redo stack because a new action diverges the timeline.
        """
        entry = HistoryEntry(image, metadata)
        self._undo_stack.append(entry)
        self._redo_stack.clear()

    def undo(self, current_image, current_metadata=None):
        """
        Pops the last state from the undo stack and returns it.
        Pushes the current state onto the redo stack.
        """
        if not self._undo_stack:
            return None

        # Save current state to redo
        current_entry = HistoryEntry(current_image, current_metadata)
        self._redo_stack.append(current_entry)

        # Restore previous state
        entry = self._undo_stack.pop()
        return entry.image, entry.metadata

    def redo(self, current_image, current_metadata=None):
        """
        Pops the next state from the redo stack and returns it.
        Pushes the current state onto the undo stack.
        """
        if not self._redo_stack:
            return None

        # Save current state to undo
        current_entry = HistoryEntry(current_image, current_metadata)
        self._undo_stack.append(current_entry)

        # Restore next state
        entry = self._redo_stack.pop()
        return entry.image, entry.metadata

    def can_undo(self):
        return len(self._undo_stack) > 0

    def can_redo(self):
        return len(self._redo_stack) > 0
