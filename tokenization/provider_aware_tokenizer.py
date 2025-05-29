from typing import Dict, Iterator
from core.models import LogLine
from tokenization.token_relationship import TokenizedSegment
from tokenization.pattern_tokenizer import PatternBasedTokenizer


class ProviderAwareTokenizer:
    """Delegates tokenization to the appropriate tokenizer based on provider."""

    def __init__(self, tokenizers: Dict[str, PatternBasedTokenizer], default_tokenizer: PatternBasedTokenizer, config: Dict = None):
        self.tokenizers = tokenizers
        self.default_tokenizer = default_tokenizer
        self.config = config or {}

    def tokenize_stream(self, log_lines: Iterator[LogLine]) -> Iterator[TokenizedSegment]:
        for log_line in log_lines:
            provider = getattr(log_line, "provider", None)
            tokenizer = self.tokenizers.get(provider, self.default_tokenizer)
            yield from tokenizer.tokenize_stream([log_line])
