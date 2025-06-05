from typing import Dict, Any, Iterator, List, Optional, Tuple
from tokenization.grouped_segment import GroupedSegment
import re
# =============================================================================
# === ContextAnalyzer: For GroupedSegment context inference
# =============================================================================
class ContextAnalyzer:
    """Analyzes relationships between segments to establish context."""

    def __init__(self,
                 window_size: int = 5,
                 providers_config: Dict[str, Dict[str, Any]] = None,
                 config: Dict[str, Any] = None):
        self.window_size = window_size
        self.providers_config = providers_config or {}
        self.config = config or {}

    def analyze(self, segments: Iterator[GroupedSegment]) -> Iterator[GroupedSegment]:
        """Analyze segments with a sliding window to establish context."""
        segment_buffer = []

        for segment in segments:
            segment_buffer.append(segment)
            if len(segment_buffer) > self.window_size:
                enriched_segment = self._analyze_buffered_context(segment_buffer)
                yield enriched_segment
                segment_buffer.pop(0)

        while segment_buffer:
            enriched_segment = self._analyze_buffered_context(segment_buffer)
            yield enriched_segment
            segment_buffer.pop(0)

    def _analyze_buffered_context(self, buffer: List[GroupedSegment]) -> GroupedSegment:
        target_segment = buffer[len(buffer) // 2]

        preceding = buffer[:len(buffer) // 2]
        if preceding:
            target_segment.context['preceding_context'] = self._extract_context_summary(preceding)

        following = buffer[len(buffer) // 2 + 1:]
        if following:
            target_segment.context['following_context'] = self._extract_context_summary(following)

        provider = target_segment.context.get('provider')
        if provider and provider in self.providers_config:
            self._apply_provider_specific_analysis(target_segment, buffer, provider)

        return target_segment

    def _extract_context_summary(self, segments: List[GroupedSegment]) -> Dict[str, Any]:
        """Extract a summary of the context from segments."""
        # Placeholder for summary extraction logic
        return {}

    def _apply_provider_specific_analysis(self,
                                          segment: GroupedSegment,
                                          buffer: List[GroupedSegment],
                                          provider: str) -> None:
        """Apply provider-specific context analysis rules."""
        provider_config = self.providers_config.get(provider, {})
        # Placeholder for rule-based customization
        pass


# =============================================================================
# === ContextDetector: For LogLine stream pattern tracking
# =============================================================================
class ContextDetector:
    """Detects context boundaries and relationships in LogLine streams."""

    # Placeholder regex lists
    STACK_TRACE_START_PATTERNS = [
        r"Traceback \(most recent call last\):",
        r"Exception in thread .*?:",
        r"java\.lang\.Throwable",
    ]
    CONTINUATION_PATTERNS = [
        r"^\s+at .*",  # Java stack trace
        r"^\s+File .*",  # Python trace
    ]
    NESTED_ERROR_PATTERNS = [
        r"Caused by:",
        r"During handling of the above exception, another exception occurred:"
    ]

    # From code_snippet_11.py
    TEST_FAILURE_PATTERNS = [
        r"^FAIL: test_\w+",
        r"^Tests failed: \d+ failures found",
        r"^AssertionError:"
    ]

    def detect_context_start(self, log_line: Any, line_index: int) -> Optional[str]:
        """Identifies the start of new error-related context."""
        for pattern in self.STACK_TRACE_START_PATTERNS + self.TEST_FAILURE_PATTERNS:
            if re.search(pattern, log_line.raw_content):
                return f"context_start_{line_index}"
        return None

    def is_continuation(self, log_line: Any, line_index: int) -> List[str]:
        """Detect if line continues a previously opened context."""
        matches = []
        for pattern in self.CONTINUATION_PATTERNS:
            if re.search(pattern, log_line.raw_content):
                matches.append(f"context_continued_{line_index}")
        return matches

    def finalize_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """Finalize and return a context summary."""
        return {"context_id": context_id, "summary": "context complete"}

    def expire_old_contexts(self, current_line: Any, max_gap: int = 3) -> List[Dict[str, Any]]:
        """Expire lingering open contexts."""
        # Simplified placeholder
        return []
