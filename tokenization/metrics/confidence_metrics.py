from typing import List, Dict, Optional
from collections import Counter
from dataclasses import dataclass
from tokenization.models import TokenizedSegment
from tokenization.rules.contextual_rule import ContextualRule
from tokenization.classifiers.base_classifier import BaseRootCauseClassifier


@dataclass
class ConfidenceMetrics:
    token_entropy: float = 0.0
    pattern_specificity: float = 0.0
    segment_coverage: float = 0.0
    segment_score: float = 0.0
    context_support: float = 0.0
    historical_accuracy: float = 0.0
    cross_segment_coherence: float = 0.0
    provider_reliability: float = 0.0

    def weighted_confidence(self, weights: Dict[str, float]) -> float:
        return min(1.0, max(0.0, sum(getattr(self, k) * w for k, w in weights.items())))


class ConfidenceScorer:
    def __init__(self,
                 feedback_history: Optional[Dict[str, Dict[str, float]]] = None,
                 provider_reliability_map: Optional[Dict[str, float]] = None,
                 token_importance_map: Optional[Dict[str, float]] = None,
                 metric_weights: Optional[Dict[str, float]] = None):
        self.feedback_history = feedback_history or {}
        self.provider_reliability = provider_reliability_map or {
            "github": 0.95, "gitlab": 0.90, "jenkins": 0.85,
            "travis": 0.85, "circleci": 0.85, "azure_pipelines": 0.85, "unknown": 0.75
        }
        self.token_importance = token_importance_map or {
            "ERROR": 1.0, "EXCEPTION": 1.0, "STACK_TRACE": 0.9, "EXIT_CODE": 0.8,
            "WARNING": 0.7, "COMMAND": 0.6, "PATH": 0.5, "VERSION": 0.5,
            "PARAMETER": 0.4, "TIMESTAMP": 0.3, "INFO": 0.3, "OUTPUT": 0.2, "DEFAULT": 0.5
        }
        self.metric_weights = metric_weights or {
            "token_entropy": 0.25, "pattern_specificity": 0.20, "segment_coverage": 0.10,
            "segment_score": 0.15, "context_support": 0.10, "historical_accuracy": 0.10,
            "cross_segment_coherence": 0.05, "provider_reliability": 0.05
        }
        self.pattern_specificity_cache = {}

    def calculate_confidence(self,
                              segments: List[TokenizedSegment],
                              matched_segment: TokenizedSegment,
                              context_segments: List[TokenizedSegment],
                              pattern: str,
                              match_obj,
                              classifier_id: str) -> ConfidenceMetrics:
        metrics = ConfidenceMetrics()
        metrics.token_entropy = self._calculate_token_entropy(matched_segment)
        metrics.pattern_specificity = self._calculate_pattern_specificity(pattern)
        metrics.segment_coverage = self._calculate_segment_coverage(matched_segment, match_obj)
        metrics.segment_score = getattr(matched_segment, 'score', 0.5)
        metrics.context_support = self._calculate_context_support(matched_segment, context_segments)
        metrics.historical_accuracy = self._get_historical_accuracy(classifier_id, pattern)
        metrics.cross_segment_coherence = self._calculate_cross_segment_coherence([matched_segment] + context_segments)
        provider = getattr(matched_segment, 'provider', 'unknown')
        metrics.provider_reliability = self.provider_reliability.get(provider.lower(), 0.75)
        return metrics

    def compute_final_confidence(self, metrics: ConfidenceMetrics) -> float:
        return metrics.weighted_confidence(self.metric_weights)

    def _calculate_token_entropy(self, segment: TokenizedSegment) -> float:
        if not getattr(segment, 'tokens', []):
            return 0.5
        token_counts = Counter(t.token_type for t in segment.tokens)
        total = sum(token_counts.values())
        if total == 0: return 0.5
        weighted = sum((count / total) * self.token_importance.get(ttype, 0.5)
                       for ttype, count in token_counts.items())
        diversity = min(1.0, len(token_counts) / 5.0)
        return min(1.0, 0.3 + 0.7 * weighted * diversity)

    def _calculate_pattern_specificity(self, pattern: str) -> float:
        if pattern in self.pattern_specificity_cache:
            return self.pattern_specificity_cache[pattern]
        length_factor = min(1.0, len(pattern) / 100.0)
        char_class_factor = min(1.0, sum(1 for c in pattern if c in r'^$.*+?()[]{}|\\') / 10.0)
        anchors = sum(pattern.count(a) for a in [r'\b', '^', '$'])
        anchor_factor = min(1.0, anchors / 3.0)
        captures = pattern.count('(') - pattern.count('(?:')
        capture_factor = min(1.0, captures / 5.0)
        specificity = 0.4 + 0.6 * (0.3 * length_factor + 0.3 * char_class_factor +
                                   0.2 * anchor_factor + 0.2 * capture_factor)
        self.pattern_specificity_cache[pattern] = specificity
        return specificity

    def _calculate_segment_coverage(self, segment: TokenizedSegment, match_obj) -> float:
        if not match_obj or not segment.text:
            return 0.5
        start, end = match_obj.span()
        coverage = (end - start) / len(segment.text)
        if coverage < 0.05:
            return min(1.0, 0.3 + coverage * 4)
        if coverage > 0.9:
            return min(1.0, 0.7 + (coverage - 0.9) * 3)
        return min(1.0, 0.5 + coverage * 0.5)

    def _calculate_context_support(self, segment: TokenizedSegment, ctx: List[TokenizedSegment]) -> float:
        if not ctx: return 0.5
        ctx_count = min(1.0, len(ctx) / 5.0)
        high_value = {'ERROR', 'EXCEPTION', 'STACK_TRACE', 'EXIT_CODE'}
        hv_present = any(t.token_type in high_value for s in ctx for t in getattr(s, 'tokens', []))
        proximity = 0.5
        if hasattr(segment, 'line_number'):
            close = sum(1 for s in ctx if hasattr(s, 'line_number') and abs(s.line_number - segment.line_number) <= 10)
            proximity = 0.3 + 0.7 * min(1.0, close / len(ctx))
        return min(1.0, 0.5 + 0.5 * (0.4 * ctx_count + 0.4 * (0.7 if hv_present else 0.3) + 0.2 * proximity))

    def _get_historical_accuracy(self, classifier_id: str, pattern: str) -> float:
        history = self.feedback_history.get(classifier_id, {})
        if pattern in history:
            return history[pattern]
        return sum(history.values()) / len(history) if history else 0.7

    def _calculate_cross_segment_coherence(self, segments: List[TokenizedSegment]) -> float:
        if len(segments) < 2: return 0.5
        sections = [getattr(s, 'section', '') for s in segments]
        section_consistent = all(s == sections[0] for s in sections)
        tokens = [t.token_type for s in segments for t in getattr(s, 'tokens', [])]
        type_counts = Counter(tokens)
        primary_ratio = (type_counts.most_common(1)[0][1] / len(tokens)) if tokens else 0.5
        type_coherence = 0.3 + 0.7 * primary_ratio
        if all(hasattr(s, 'line_number') for s in segments):
            span = max(s.line_number for s in segments) - min(s.line_number for s in segments)
            line_proximity = 0.9 if span <= 5 else 0.7 if span <= 20 else 0.5 if span <= 50 else 0.3
        else:
            line_proximity = 0.5
        return min(1.0, 0.3 + 0.7 * (0.4 * (1.0 if section_consistent else 0.5) +
                                     0.4 * type_coherence + 0.2 * line_proximity))


class EnhancedRuleBasedClassifier(BaseRootCauseClassifier):
    def __init__(self, name: str, threshold: float = 0.7, scorer: Optional[ConfidenceScorer] = None):
        self.name = name
        self.confidence_threshold = threshold
        self.classifier_id = f"{self.__class__.__name__}:{id(self)}"
        self.rules: List[ContextualRule] = []
        self.confidence_scorer = scorer or ConfidenceScorer()
        self._initialize_rules()

    def _initialize_rules(self):
        pass  # Rules should be added in subclasses or setup methods

    def _calculate_confidence(self,
                               segments: List[TokenizedSegment],
                               segment: TokenizedSegment,
                               context_segments: List[TokenizedSegment],
                               rule_name: str,
                               pattern: str,
                               match_obj) -> float:
        metrics = self.confidence_scorer.calculate_confidence(
            segments, segment, context_segments, pattern, match_obj, self.classifier_id
        )
        return self.confidence_scorer.compute_final_confidence(metrics)
