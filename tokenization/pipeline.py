from typing import Dict, Any, Iterator, Optional, Union
from core.models import LogLine
from tokenization.token_relationship import TokenizedSegment
from tokenization.grouped_segment import GroupedSegment
from tokenization.segment_classifier import SegmentClassifier
from tokenization.context_analyzer import ContextAnalyzer
from tokenization.grouping import GroupingStrategy

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
        tokenized_segments = self.tokenize_stream(log_lines)
        classified_segments = self.classify_segments(tokenized_segments)
        grouped_segments = self.group_segments(classified_segments)
        enriched_segments = self.enrich_with_context(grouped_segments)
        scoped_segments = self.apply_scoping(enriched_segments)
        return scoped_segments

    def tokenize_stream(self, log_lines: Iterator[LogLine]) -> Iterator[TokenizedSegment]:
        return self.tokenizer.tokenize_stream(log_lines)

    def classify_segments(self, segments: Iterator[TokenizedSegment]) -> Iterator[TokenizedSegment]:
        for segment in segments:
            if isinstance(segment, TokenizedSegment):
                yield self.segment_classifier.classify(segment)

    def group_segments(self, segments: Iterator[TokenizedSegment]) -> Iterator[GroupedSegment]:
        return self.grouping_strategy.group(segments)

    def enrich_with_context(self, segments: Iterator[GroupedSegment]) -> Iterator[GroupedSegment]:
        return self.context_analyzer.analyze(segments)

    def apply_scoping(self, segments: Iterator[GroupedSegment]) -> Iterator[TokenizedSegment]:
        for segment in segments:
            if not hasattr(segment, "context"):
                continue
            if "scope_cues" in segment.context:
                segment.scope = self._determine_scope(segment)
            yield segment

    def _determine_scope(self, segment: GroupedSegment) -> str:
        return "default-scope"
