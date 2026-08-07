from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any, Optional, Union
from ..draft import SpriteDraft

class AIProvider(ABC):
    """
    Abstract base class for AI Providers.
    Different backends (e.g. OpenAI, Local Models, Stub/Procedural)
    should implement this interface.
    """

    @abstractmethod
    def generate_sprite(
        self,
        prompt: str,
        size: Tuple[int, int],
        style_context: Optional[Dict[str, Any]] = None,
        palette_context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Union[SpriteDraft, Any]:
        """
        Generates a sprite based on a prompt and constraints.
        Returns a SpriteDraft object or SpriteWorkspace.
        """
        pass
