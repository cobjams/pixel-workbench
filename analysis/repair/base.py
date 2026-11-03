from abc import ABC, abstractmethod
from typing import Optional
from ...core.document import Document
from ..sprite_analysis import SpriteAnalysis

class RepairRule(ABC):
    @abstractmethod
    def applies(self, document: Document, analysis: SpriteAnalysis) -> bool:
        pass

    @abstractmethod
    def repair(self, document: Document, analysis: SpriteAnalysis) -> None:
        pass

    @abstractmethod
    def explain(self) -> str:
        pass
