from typing import Dict, Any, Iterator, Optional
from core.models import LogLine
from tokenization.token_relationship import TokenizedSegment
from tokenization.grouped_segment import GroupedSegment
from tokenization.segment_classifier import SegmentClassifier
from tokenization.context_analyzer import ContextAnalyzer
from tokenization.grouping import GroupingStrategy


class TokenizationPipeline:
    def __init__(
        self,
        tokenizer,  # Expected to have a .tokenize_stream() method
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
        if tokenized_segments is None:
            tokenized_segments = iter([])

        classified_segments = self.classify_segments(tokenized_segments)
        if classified_segments is None:
            classified_segments = iter([])

        grouped_segments = self.group_segments(classified_segments)
        if grouped_segments is None:
            grouped_segments = iter([])

        enriched_segments = self.enrich_with_context(grouped_segments)
        if enriched_segments is None:
            enriched_segments = iter([])

        scoped_segments = self.apply_scoping(enriched_segments)
        if scoped_segments is None:
            scoped_segments = iter([])

        return scoped_segments

    def tokenize_stream(self, log_lines: Iterator[LogLine]) -> Optional[Iterator[TokenizedSegment]]:
        return self.tokenizer.tokenize_stream(log_lines)

    def classify_segments(self, segments: Iterator[TokenizedSegment]) -> Optional[Iterator[TokenizedSegment]]:
        if segments is None:
            return iter([])
        return (self.segment_classifier.classify(segment) for segment in segments)

    def group_segments(self, segments: Iterator[TokenizedSegment]) -> Optional[Iterator[GroupedSegment]]:
        if segments is None:
            return iter([])
        return self.grouping_strategy.group(segments)

    def enrich_with_context(self, segments: Iterator[GroupedSegment]) -> Optional[Iterator[GroupedSegment]]:
        if segments is None:
            return iter([])
        return self.context_analyzer.analyze(segments)

    def apply_scoping(self, segments: Iterator[GroupedSegment]) -> Iterator[TokenizedSegment]:
        if segments is None:
            return iter([])
        for segment in segments:
            if segment.context.get("scope_cues"):
                segment.scope = self._determine_scope(segment)
            yield segment  # assumed to be TokenizedSegment-compatible

    def _determine_scope(self, segment: GroupedSegment) -> str:
        return "default-scope"  # placeholder scope determination logic
