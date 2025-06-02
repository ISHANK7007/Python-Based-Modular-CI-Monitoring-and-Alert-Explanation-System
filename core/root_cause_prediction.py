from typing import List, Dict
from tokenization.token_relationship import TokenizedSegment
from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class RootCausePrediction:
    """
    Structured output for root cause classification.

    Attributes:
        label: The predicted root cause label (string).
        confidence: Confidence score between 0.0 and 1.0.
        segment_ids: List of segment IDs associated with this prediction.
        metadata: Optional dictionary of additional metadata.
    """
    label: str
    confidence: float
    segment_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

# --- Base classifier ---
class BaseClassifier:
    def __init__(self, name: str, label: str):
        self.name = name
        self.label = label
        self.classifier_id = name

    def classify(self, segments: List[TokenizedSegment]) -> List[RootCausePrediction]:
        raise NotImplementedError("Subclasses must implement classify()")


# --- Specific classifiers ---
class BuildFailureClassifier(BaseClassifier):
    def classify(self, segments: List[TokenizedSegment]) -> List[RootCausePrediction]:
        predictions = []
        for seg in segments:
            if any("compilation failed" in t.lower() or "exit code" in t.lower() for t in seg.tokens):
                predictions.append(RootCausePrediction(
                    label=self.label,
                    confidence=0.9,
                    segment_ids=[seg.segment_id],  # <- pass list of segment ids here
                    metadata={"reason": "Build failure detected"}
                ))
        return predictions


class OutOfMemoryClassifier(BaseClassifier):
    def classify(self, segments: List[TokenizedSegment]) -> List[RootCausePrediction]:
        predictions = []
        for seg in segments:
            if any("out of memory" in t.lower() or "heap space" in t.lower() for t in seg.tokens):
                predictions.append(RootCausePrediction(
                    label=self.label,
                    confidence=0.85,
                    segment_ids=[seg.segment_id],  # <- pass list of segment ids here
                    metadata={"reason": "OOM condition detected"}
                ))
        return predictions


class MissingDependencyClassifier(BaseClassifier):
    def classify(self, segments: List[TokenizedSegment]) -> List[RootCausePrediction]:
        predictions = []
        for seg in segments:
            if any("missing dependency" in t.lower() or "cannot find module" in t.lower() for t in seg.tokens):
                predictions.append(RootCausePrediction(
                    label=self.label,
                    confidence=0.8,
                    segment_ids=[seg.segment_id],  # <- pass list of segment ids here
                    metadata={"reason": "Missing dependency"}
                ))
        return predictions


# --- Registry for managing classifiers ---
class RootCauseClassifierRegistry:
    def __init__(self):
        self.classifiers: Dict[str, BaseClassifier] = {}

    def register(self, classifier: BaseClassifier):
        self.classifiers[classifier.classifier_id] = classifier

    def classify(self, segments: List[TokenizedSegment]) -> List[RootCausePrediction]:
        all_predictions = []
        for classifier in self.classifiers.values():
            all_predictions.extend(classifier.classify(segments))
        return all_predictions
