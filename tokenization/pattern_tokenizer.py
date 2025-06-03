import re
from typing import List, Dict, Iterator, Union, Optional, Tuple
from collections import defaultdict
from tokenization.token_types import TokenType
from tokenization.models import Token
from core.models import LogLine
from concurrent.futures import ThreadPoolExecutor

CompiledPattern = Union[str, re.Pattern]


class PatternSet:
    def __init__(self, token_type: TokenType, patterns: List[CompiledPattern],
                 priority: int = 0, flags: int = 0):
        self.token_type = token_type
        self.priority = priority
        self.flags = flags
        self.compiled_patterns = [
            re.compile(p, flags) if isinstance(p, str) else p
            for p in patterns
        ]

    def match_batch(
        self,
        texts: List[str],
        use_threading: bool = False,
        max_workers: Optional[int] = None
    ) -> List[Dict[TokenType, List[Tuple[re.Match, CompiledPattern]]]]:
        results = []

        def process(text):
            matches = {}
            for pattern in self.compiled_patterns:
                match = pattern.search(text)
                if match:
                    matches.setdefault(self.token_type, []).append((match, pattern))
            return matches

        if use_threading:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(process, texts))
        else:
            for text in texts:
                results.append(process(text))

        return results


class PatternBasedTokenizer:
    """Tokenizes log lines using pattern matching for various token types."""

    def __init__(self, patterns: Union[Dict[TokenType, List[str]], List[Dict]], config: Dict = None):
        self.patterns: Dict[TokenType, List[str]] = defaultdict(list)
        self.config = config or {}

        if isinstance(patterns, dict):
            for token_type, regex_list in patterns.items():
                self.patterns[token_type].extend(regex_list)
        elif isinstance(patterns, list):
            for pattern_def in patterns:
                if not isinstance(pattern_def, dict):
                    continue
                token_type = pattern_def.get("token_type")
                regex = pattern_def.get("regex")
                if token_type and regex:
                    self.patterns[token_type].append(regex)
        else:
            raise ValueError("patterns must be either Dict[TokenType, List[str]] or List[Dict]")

        # Add disambiguation exclusions to avoid false positives
        self.patterns[TokenType.ERROR] += [
            r"error(?!\s+(?:tolerance|bound|margin|rate|analysis|distribution|handling))"
        ]
        self.patterns[TokenType.WARNING] += [
            r"warning(?!\s+(?:level|flags|settings|policy|suppression))"
        ]

    def tokenize_stream(self, log_lines: Iterator[LogLine]) -> Iterator[Token]:
        for log_line in log_lines:
            matched_token = self._match_line_to_token(log_line)
            if matched_token:
                yield matched_token

    def _match_line_to_token(self, log_line: LogLine) -> Optional[Token]:
        """Try matching the line to a token pattern, return the token if matched."""
        for token_type, regex_list in self.patterns.items():
            for regex in regex_list:
                if re.search(regex, log_line.raw_content, re.IGNORECASE):
                    return self._create_token(log_line, token_type)
        return None

    def _create_token(self, log_line: LogLine, token_type: TokenType) -> Token:
        return Token(
            type=token_type,
            value=log_line.raw_content,
            line_reference=log_line.line_number,
            source_line=log_line
        )
