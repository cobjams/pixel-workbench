from abc import ABC, abstractmethod
from typing import Optional
from pixel_workbench.core.document import Document
from pixel_workbench.analysis.sprite_analysis import SpriteAnalysis

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
