import re
from typing import List, Dict, Iterator
from tokenization.token_types import TokenType
from tokenization.models import Token

from core.models import LogLine


class PatternBasedTokenizer:
    """Tokenizes log lines using pattern matching for various token types."""

    def __init__(self, patterns: Dict[TokenType, List[str]], config: Dict = None):
        self.patterns = patterns
        self.config = config or {}

    def tokenize_stream(self, log_lines: Iterator[LogLine]) -> Iterator:
        for log_line in log_lines:
            for token_type, regex_list in self.patterns.items():
                for regex in regex_list:
                    if re.search(regex, log_line.raw_content):
                        yield self._create_token_segment(log_line, token_type)
                        break
                else:
                    continue
                break

    def _create_token_segment(self, log_line: LogLine, token_type: TokenType):
        token = Token(
            type=token_type,
            value=log_line.raw_content,
            line_reference=log_line.line_number,
            source_line=log_line
        )
        # You'll wrap this in TokenizedSegment externally
        return token
