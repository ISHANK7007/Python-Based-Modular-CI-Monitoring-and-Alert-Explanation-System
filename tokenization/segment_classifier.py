from typing import List, Dict, Any
from tokenization.segment_rules import ClassificationRule
from tokenization.token_relationship import TokenizedSegment
from tokenization.token_types import SegmentType, TokenType
import math
from collections import Counter

# -------------------------------
# Segment Classification with Rules
# -------------------------------
class SegmentClassifier:
    """Classifies TokenizedSegments into semantic categories."""

    def __init__(self, classification_rules: List[ClassificationRule], config: Dict[str, Any] = None):
        self._rules = classification_rules
        self.config = config or {}

    def classify(self, segment: TokenizedSegment) -> TokenizedSegment:
        """Apply classification rules and scoring enhancements to a segment."""
        if not hasattr(segment, "context") or not hasattr(segment, "tokens"):
            raise TypeError("Expected TokenizedSegment with 'context' and 'tokens' fields.")

        for rule in self._rules:
            if isinstance(rule, ClassificationRule) and rule.matches(segment):
                segment.context['classification'] = rule.classification_type
                segment.context['confidence'] = rule.calculate_confidence(segment)
                segment.context.update(rule.extract_metadata(segment))

        segment.token_distribution = SegmentScorer.calculate_token_distribution(segment.tokens)
        segment.entropy = SegmentScorer.calculate_entropy(segment.raw_text)
        segment.segment_score = SegmentScorer.compute_segment_score(segment)
        segment.confidence_level = SegmentScorer.calculate_confidence_level(segment)

        return segment

    def get_classifiers(self) -> List[ClassificationRule]:
        """Expose registered classification rules."""
        return self._rules

# -------------------------------
# SimpleSegmentClassifier for Testing
# -------------------------------
class SimpleSegmentClassifier:
    """Minimal rule-free fallback classifier used in test pipelines."""

    def classify(self, segment: TokenizedSegment) -> TokenizedSegment:
        if not hasattr(segment, "context") or not hasattr(segment, "tokens"):
            raise TypeError("Expected TokenizedSegment with 'context' and 'tokens' fields.")

        segment.segment_type = SegmentType.DEFAULT
        segment.context["classification"] = "default"
        segment.context["confidence"] = 0.5

        segment.token_distribution = SegmentScorer.calculate_token_distribution(segment.tokens)
        segment.entropy = SegmentScorer.calculate_entropy(segment.raw_text)
        segment.segment_score = SegmentScorer.compute_segment_score(segment)
        segment.confidence_level = SegmentScorer.calculate_confidence_level(segment)

        return segment

# -------------------------------
# SegmentScorer
# -------------------------------
class SegmentScorer:
    """Utility class for segment-level statistical scoring."""

    @staticmethod
    def calculate_token_distribution(tokens: List[Any]) -> Dict[TokenType, int]:
        return dict(Counter(token.type for token in tokens))

    @staticmethod
    def calculate_entropy(text: str) -> float:
        if not text:
            return 0.0
        char_counts = Counter(text)
        total_chars = len(text)
        entropy = -sum((count / total_chars) * math.log2(count / total_chars) for count in char_counts.values())
        return entropy

    @staticmethod
    def compute_segment_score(segment: TokenizedSegment) -> float:
        severity_score = sum(token.type.severity.level for token in segment.tokens)
        length_penalty = max(len(segment.tokens), 1)
        return round(severity_score / length_penalty, 2)

    @staticmethod
    def calculate_confidence_level(segment: TokenizedSegment) -> float:
        severity = segment.segment_score
        entropy_penalty = max(1.0 - (segment.entropy / 10.0), 0)
        return round(min(1.0, severity / 100 * entropy_penalty), 2)
