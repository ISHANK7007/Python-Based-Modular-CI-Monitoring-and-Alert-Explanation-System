from typing import Dict, Iterator, Any, Tuple, Deque, List
from collections import deque

from core.models import LogLine
from tokenization.models import Token, ContextualSegment
from tokenization.pattern_tokenizer import PatternBasedTokenizer
from tokenization.token_relationship import TokenizedSegment
from tokenization.context_analyzer import ContextDetector


class ProviderAwareTokenizer:
    """
    Delegates tokenization to the appropriate tokenizer based on provider,
    supporting both classic and context-aware tokenizers.
    """

    def __init__(
        self,
        tokenizers: Dict[str, Any],  # Can be PatternBasedTokenizer or ContextualBufferedTokenizer
        default_tokenizer: Any,
        config: Dict = None
    ):
        self.tokenizers = tokenizers
        self.default_tokenizer = default_tokenizer
        self.config = config or {}

    def tokenize_stream(self, log_lines: Iterator[LogLine]) -> Iterator[TokenizedSegment]:
        for log_line in log_lines:
            provider = getattr(log_line, "provider", None)
            tokenizer = self.tokenizers.get(provider, self.default_tokenizer)
            yield from tokenizer.tokenize_stream([log_line])


class ContextualBufferedTokenizer:
    """
    Tokenizer that maintains a rolling buffer to apply context-aware logic.
    """

    def __init__(self, patterns: Dict, config: Dict = None):
        self.patterns = patterns
        self.config = config or {}
        self.buffer_size = self.config.get('context_buffer_size', 50)
        self.line_buffer: Deque[Tuple[Any, TokenizedSegment]] = deque(maxlen=self.buffer_size)
        self.context_analyzer = ContextDetector()
        self.pending_segments: Dict[int, ContextualSegment] = {}

    def tokenize_stream(self, log_lines: Iterator[Any]) -> Iterator[ContextualSegment]:
        current_index = 0

        for line in log_lines:
            matched_tokens = self._match_tokens(line)
            segment = self._create_segment(line, matched_tokens, current_index)
            self.line_buffer.append((line, segment))

            # Trigger processing if buffer is full
            if len(self.line_buffer) >= self.buffer_size:
                yield from self._process_buffer(current_index)

            current_index += 1

        # Flush remaining
        yield from self._process_buffer(current_index, final_batch=True)

    def _match_tokens(self, log_line: LogLine) -> List[Token]:
        matched = []
        for token_type, regex_list in self.patterns.items():
            for pattern in regex_list:
                if pattern.search(log_line.raw_content):
                    matched.append(Token(
                        type=token_type,
                        value=log_line.raw_content,
                        line_reference=log_line.line_number,
                        source_line=log_line
                    ))
        return matched

    def _create_segment(self, log_line: LogLine, tokens: List[Token], index: int) -> ContextualSegment:
        return ContextualSegment(
            tokens=tokens,
            raw_text=log_line.raw_content,
            line_range=(log_line.line_number, log_line.line_number),
            context={"provider": getattr(log_line, "provider", None)},
            confidence_level=1.0,
            segment_score=0.0,
            context_clues=[],
            related_segments=[],
            is_continuation=False,
            context_start_line=index,
            parent_context=None
        )

    def _process_buffer(self, current_line_idx: int, final_batch: bool = False) -> List[ContextualSegment]:
        segments = [seg for (_, seg) in self.line_buffer]
        return list(self.context_analyzer.analyze(iter(segments)))
