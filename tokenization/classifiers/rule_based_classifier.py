from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Pattern
import re

from core.root_cause_prediction import RootCausePrediction
from tokenization.models import TokenizedSegment

# === Abstract Base ===
class BaseRootCauseClassifier(ABC):
    @abstractmethod
    def classify(self, segments: List[TokenizedSegment]) -> List[RootCausePrediction]:
        pass

# === Rule-Based Framework ===
class RuleBasedClassifier(BaseRootCauseClassifier):
    def __init__(self, name: str, confidence_threshold: float = 0.7):
        self.name = name
        self.confidence_threshold = confidence_threshold
        self.classifier_id = self._generate_classifier_id()
        self._initialize_rules()

    @abstractmethod
    def _initialize_rules(self) -> None:
        pass

    def _generate_classifier_id(self) -> str:
        return f"{self.__class__.__name__}:{id(self)}"

    @abstractmethod
    def match(self, segment: TokenizedSegment) -> Optional[RootCausePrediction]:
        pass

    def classify(self, segments: List[TokenizedSegment]) -> List[RootCausePrediction]:
        return [pred for segment in segments if (pred := self.match(segment))]

    def batch_classify(self, batch_segments: List[List[TokenizedSegment]]) -> List[List[RootCausePrediction]]:
        return [self.classify(segments) for segments in batch_segments]

# === Pattern-Based Rule Matcher ===
class PatternBasedClassifier(RuleBasedClassifier):
    def __init__(self, name: str, label: str, confidence_threshold: float = 0.7):
        self.label = label
        self.patterns: List[Pattern] = []
        self.supporting_token_extractors: Dict[Pattern, callable] = {}
        super().__init__(name, confidence_threshold)

    def add_pattern(self, pattern: str, supporting_token_extractor: callable = None):
        compiled_pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        self.patterns.append(compiled_pattern)
        if supporting_token_extractor:
            self.supporting_token_extractors[compiled_pattern] = supporting_token_extractor

    def match(self, segment: TokenizedSegment) -> Optional[RootCausePrediction]:
        for pattern in self.patterns:
            match = pattern.search(segment.raw_text)
            if match:
                confidence = self._calculate_confidence(segment, match)
                if confidence >= self.confidence_threshold:
                    supporting_tokens = []
                    if pattern in self.supporting_token_extractors:
                        supporting_tokens = self.supporting_token_extractors[pattern](match)
                    return RootCausePrediction(
                        label=self.label,
                        confidence=confidence,
                        segment_ids=[getattr(segment, "segment_id", "unknown")],
                        supporting_tokens=supporting_tokens,
                        provider_context=self._extract_provider_context(segment),
                        metadata={"pattern_matched": pattern.pattern},
                        classifier_id=self.classifier_id
                    )
        return None

    def _calculate_confidence(self, segment: TokenizedSegment, match) -> float:
        base_confidence = 0.8
        if getattr(segment, 'segment_score', 0) > 0.7:
            base_confidence += 0.1
        return min(base_confidence, 1.0)

    def _extract_provider_context(self, segment: TokenizedSegment) -> Dict[str, Any]:
        return {'provider': getattr(segment, 'provider', None)} if hasattr(segment, 'provider') else {}

# === Concrete Classifiers ===
class BuildFailureClassifier(PatternBasedClassifier):
    def _initialize_rules(self):
        self.add_pattern(r"build failed|compilation failed|failed to compile", lambda m: ["build failed"])
        self.add_pattern(r"ERROR: Build failed with an exception", lambda m: ["build exception"])
        self.add_pattern(r"Failed to execute goal .* compile", lambda m: ["maven compile"])
        self.add_pattern(r"error: cannot find symbol", lambda m: ["missing symbol"])
        self.add_pattern(r"build step.*?failed|compilation.*?failed", lambda m: ["build failed"])
        self.add_pattern(r"\berror\b.*\bcompile|compilation", lambda m: ["compilation error"])


class OutOfMemoryClassifier(PatternBasedClassifier):
    def _initialize_rules(self):
        self.add_pattern(r"java\\.lang\\.OutOfMemoryError", lambda m: ["java OOM"])
        self.add_pattern(r"Killed\\s+.*\\s+\\(Out of memory\\)", lambda m: ["process killed", "OOM"])
        self.add_pattern(r"memory exhausted|not enough memory", lambda m: ["memory exhausted"])

class MissingDependencyClassifier(PatternBasedClassifier):
    def _initialize_rules(self):
        self.add_pattern(r"could not find|not found in the repositories|missing artifact", lambda m: ["missing artifact"])
        self.add_pattern(r"Failed to resolve (\\S+)", lambda m: [f"unresolved: {m.group(1)}"])
        self.add_pattern(r"ModuleNotFoundError: No module named '([^']+)'", lambda m: [f"missing module: {m.group(1)}"])

# === Registry ===
class RootCauseClassifierRegistry:
    def __init__(self):
        self.classifiers: Dict[str, RuleBasedClassifier] = {}

    def register(self, classifier: RuleBasedClassifier) -> None:
        self.classifiers[classifier.name] = classifier

    def classify(self, segments: List[TokenizedSegment]) -> List[RootCausePrediction]:
        all_predictions = []
        for classifier in self.classifiers.values():
            all_predictions.extend(classifier.classify(segments))
        return sorted(all_predictions, key=lambda p: p.confidence, reverse=True)
