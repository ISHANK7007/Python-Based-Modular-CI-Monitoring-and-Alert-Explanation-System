import collections
from typing import Dict, Any, Iterator, Optional, List

from core.models import LogLine
from tokenization.models import Token
from tokenization.token_types import TokenType, TokenTypeSeverity
from tokenization.token_relationship import TokenizedSegment
from tokenization.grouped_segment import GroupedSegment
from tokenization.segment_classifier import SegmentClassifier
from tokenization.context_analyzer import ContextAnalyzer
from tokenization.grouping import GroupingStrategy
from tokenization.resolution import TokenConflictResolver
from tokenization.context_classifier import EnhancedTokenClassifier

# Optional advanced components
from tokenization.registry import ContextAwareTokenizerRegistry
from tokenization.tokenizer import BatchedPatternTokenizer
from tokenization.tokenization_cache import CachedTokenizer
from tokenization.resolution import FalsePositiveAwareTokenizer, register_custom_false_positive_filters


# =============================================================================
# === Config (from snippet 12)
# =============================================================================
default_pipeline_config = {
    'context_buffer_size': 50,
    'min_context_lines': 3,
    'max_trace_lines': 100,
    'pending_threshold': 10,
    'enable_nested_errors': True,
    'provider_context_adjustments': {
        'jenkins': {
            'max_trace_lines': 60,
            'nested_error_weight': 1.2,
        }
    }
}


# =============================================================================
# === TokenizationPipeline (Base)
# =============================================================================
class TokenizationPipeline:
    def __init__(
        self,
        tokenizer,
        segment_classifier: SegmentClassifier,
        context_analyzer: ContextAnalyzer,
        grouping_strategy: GroupingStrategy,
        config: Optional[Dict[str, Any]] = None
    ):
        self.tokenizer = tokenizer
        self.segment_classifier = segment_classifier
        self.context_analyzer = context_analyzer
        self.grouping_strategy = grouping_strategy
        self.config = config or {}

    def process(self, log_lines: Iterator[LogLine]) -> Iterator[TokenizedSegment]:
        tokenized_segments = self.tokenize_stream(log_lines) or iter([])
        classified_segments = self.classify_segments(tokenized_segments) or iter([])
        grouped_segments = self.group_segments(classified_segments) or iter([])
        enriched_segments = self.enrich_with_context(grouped_segments) or iter([])
        scoped_segments = self.apply_scoping(enriched_segments) or iter([])
        return scoped_segments

    def tokenize_stream(self, log_lines: Iterator[LogLine]) -> Optional[Iterator[TokenizedSegment]]:
        return self.tokenizer.tokenize_stream(log_lines)

    def classify_segments(self, segments: Iterator[TokenizedSegment]) -> Optional[Iterator[TokenizedSegment]]:
        return (self.segment_classifier.classify(segment) for segment in segments)

    def group_segments(self, segments: Iterator[TokenizedSegment]) -> Optional[Iterator[GroupedSegment]]:
        return self.grouping_strategy.group(segments)

    def enrich_with_context(self, segments: Iterator[GroupedSegment]) -> Optional[Iterator[GroupedSegment]]:
        return self.context_analyzer.analyze(segments)

    def apply_scoping(self, segments: Iterator[GroupedSegment]) -> Iterator[TokenizedSegment]:
        for segment in segments:
            if segment.context.get("scope_cues"):
                segment.scope = self._determine_scope(segment)
            yield segment

    def _determine_scope(self, segment: GroupedSegment) -> str:
        return "default-scope"


# =============================================================================
# === ConflictAwareTokenizationPipeline
# =============================================================================
class ConflictAwareTokenizationPipeline(TokenizationPipeline):
    """Tokenization pipeline with conflict resolution and structural awareness."""

    def __init__(self, provider: str, tokenizer, config: Optional[Dict[str, Any]] = None):
        super().__init__(tokenizer, None, None, None, config)
        self.provider = provider
        self.conflict_resolver = TokenConflictResolver(provider)
        self.context_window = collections.deque(maxlen=10)

    def process(self, log_lines: Iterator[LogLine]) -> Iterator[TokenizedSegment]:
        classifier = EnhancedTokenClassifier(self.provider)
        classified_tokens = []
        token_types_history = collections.deque(maxlen=5)

        for line in log_lines:
            self.context_window.append(line)
            classifier.context['prev_line_types'] = list(token_types_history)
            token = classifier.classify_line(line)
            token_types_history.append(token.type)
            classified_tokens.append(token)

        grouped_tokens = []
        current_group = []
        current_section = None
        current_stream = None

        for token in classified_tokens:
            source_line = token.source_line

            if current_section and source_line.section != current_section:
                if not self._allow_cross_section(current_group, token):
                    if current_group:
                        grouped_tokens.append(current_group)
                        current_group = []

            if current_stream and source_line.stream_type != current_stream:
                if not self._allow_cross_stream(current_group, token):
                    if current_group:
                        grouped_tokens.append(current_group)
                        current_group = []

            current_section = source_line.section
            current_stream = source_line.stream_type
            current_group.append(token)

            if self._is_group_separator(token):
                grouped_tokens.append(current_group)
                current_group = []

        if current_group:
            grouped_tokens.append(current_group)

        segments = [self._create_segment_from_group(group) for group in grouped_tokens if group]
        return iter(segments)

    def _allow_cross_section(self, current_group: List[Token], next_token: Token) -> bool:
        if not current_group:
            return False
        last_token = current_group[-1]
        return (last_token.type == TokenType.STACK_TRACE and next_token.type == TokenType.STACK_TRACE) or \
               (last_token.type in (TokenType.ERROR,) and next_token.type in (TokenType.ERROR, TokenType.STACK_TRACE))

    def _allow_cross_stream(self, current_group: List[Token], next_token: Token) -> bool:
        if not current_group:
            return False
        last_token = current_group[-1]
        return (
            last_token.type.severity >= TokenTypeSeverity(100, "error").level and
            next_token.type.severity >= TokenTypeSeverity(100, "error").level
        )

    def _is_group_separator(self, token: Token) -> bool:
        if token.type.name in ("SECTION_START", "SECTION_END", "STEP_START", "STEP_END"):
            return True
        if self.provider == 'github_actions':
            return token.value.startswith("##[group]") or token.value.startswith("##[endgroup]")
        if self.provider == 'gitlab_ci':
            return 'section_start:' in token.value or 'section_end:' in token.value
        return False

    def _create_segment_from_group(self, group: List[Token]) -> TokenizedSegment:
        primary_type = max([t.type for t in group], key=lambda t: t.severity.level)
        first = group[0]
        last = group[-1]
        return TokenizedSegment(
            segment_id=f"{self.provider}_{first.line_reference}_{last.line_reference}",
            tokens=group,
            segment_type=primary_type.name,
            confidence=1.0,
            context=self._extract_context(group),
            start_line=first.line_reference,
            end_line=last.line_reference,
            provider=self.provider,
            related_segments=[],
        )

    def _extract_context(self, group: List[Token]) -> Dict[str, Any]:
        context = {}
        if group:
            context['section'] = group[0].source_line.section
            context['stream'] = group[0].source_line.stream_type
            context['step'] = group[0].source_line.step_name
            context['token_type_distribution'] = {
                t.name: sum(1 for token in group if token.type == t)
                for t in set(token.type for token in group)
            }
        return context


# =============================================================================
# === Example Tokenizer Construction (from snippets 10, 18, 21)
# =============================================================================

def build_tokenizer_with_cache_and_fpp(patterns, cache, config):
    """Builds a tokenizer with false positive prevention and caching."""
    tokenizer = FalsePositiveAwareTokenizer(
        patterns=patterns,
        config={
            'false_positive_mode': 'adjust',
            'min_confidence_threshold': 0.4,
            'enable_ml_false_positive_detection': True,
            **(config or {})
        }
    )
    register_custom_false_positive_filters(tokenizer)
    return CachedTokenizer(tokenizer, cache)
