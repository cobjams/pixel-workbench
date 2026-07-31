import time
from typing import Optional, Dict, Any, List
from ..core.document import Document

class SpriteDraft:
    """
    A wrapper class for generated sprites before they are accepted into the main editor.
    Keeps AI-specific metadata separate from the core Document.
    """
    def __init__(
        self,
        document: Document,
        prompt: str = "",
        generator: str = "",
        model: str = "",
        generation_time: Optional[float] = None,
        review: Optional[Dict[str, Any]] = None,
        validation: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.document = document
        self.prompt = prompt
        self.generator = generator
        self.model = model
        self.generation_time = generation_time or time.time()
        self.review = review or {}
        self.validation = validation or {}
        self.metadata = metadata or {}
        self.thumbnail = None  # Could hold a base64 string or smaller image object later

    def to_dict(self) -> Dict[str, Any]:
        """Returns a machine-readable summary of the draft."""
        return {
            "prompt": self.prompt,
            "generator": self.generator,
            "model": self.model,
            "generation_time": self.generation_time,
            "review": self.review,
            "validation": self.validation,
            "metadata": self.metadata,
            "size": (self.document.width, self.document.height) if self.document and self.document.image else None,
        }
