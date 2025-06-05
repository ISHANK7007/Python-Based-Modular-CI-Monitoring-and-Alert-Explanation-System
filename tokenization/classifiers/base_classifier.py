from typing import List, Any
from abc import ABC, abstractmethod
from tokenization.models import TokenizedSegment

class BaseRootCauseClassifier(ABC):
    """
    Base abstract classifier for identifying root cause segments.
    """
    @abstractmethod
    def classify(self, segments: List[TokenizedSegment]) -> List[Any]:
        pass
