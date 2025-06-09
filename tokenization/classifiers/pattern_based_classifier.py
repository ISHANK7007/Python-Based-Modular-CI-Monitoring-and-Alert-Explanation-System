import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from tokenization.segment_type import SegmentType
from tokenization.token import Token


class PatternBasedClassifier(ABC):
    """
    Abstract base class for rule-based token classifiers that match tokens
    against predefined regex patterns to assign segment types.
    """

    def __init__(self, name: str, label: str):
        self.name = name
        self.label = label
        self.rules: List[Dict[str, Any]] = []
        self._initialize_rules()

    def classify(self, token: Token) -> SegmentType:
        """
        Apply all patterns to the token text and return a matching SegmentType.
        If no match is found, returns SegmentType.DEFAULT.
        """
        for rule in self.rules:
            pattern: re.Pattern = rule["pattern"]
            if pattern.search(token.text):
                return SegmentType[self.label]
        return SegmentType.DEFAULT

    @abstractmethod
    def _initialize_rules(self):
        """
        Subclasses must implement this method to populate self.rules
        with a list of pattern dictionaries: {"pattern": re.Pattern}.
        """
        pass


# Optional concrete subclass for testing or example usage
class TestBuildFailureClassifier(PatternBasedClassifier):
    def __init__(self):
        super().__init__(name="test_build_failure", label="BUILD_FAILURE")

    def _initialize_rules(self):
        self.rules = [
            {"pattern": re.compile(r"cannot find symbol", re.IGNORECASE)},
            {"pattern": re.compile(r"compilation failed", re.IGNORECASE)},
            {"pattern": re.compile(r"BUILD FAILURE", re.IGNORECASE)},
        ]
