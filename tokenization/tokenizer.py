from typing import List
from core.models import LogLine
from tokenization.token_types import Token, TokenType, TokenizedSegment, SegmentType

class BasicTokenizer:
    def tokenize_stream(self, log_lines: List[LogLine]) -> List[TokenizedSegment]:
        segments = []
        for idx, log_line in enumerate(log_lines):
            token = Token(
                type=self._classify_line(log_line.message),
                value=log_line.message,
                line_reference=log_line.line_number,
                source_line=log_line
            )
            segment = TokenizedSegment(
                segment_id=f"seg_{idx}",
                tokens=[token],
                segment_type=SegmentType.DEFAULT,
                confidence=1.0,
                context={},
                start_line=log_line.line_number,
                end_line=log_line.line_number,
                provider=log_line.source

            )
            segments.append(segment)
        return segments

    def _classify_line(self, line: str) -> TokenType:
        if "error" in line.lower():
            return TokenType.ERROR
        elif "warning" in line.lower():
            return TokenType.WARNING
        elif "fail" in line.lower():
            return TokenType.TEST_FAILURE
        elif "##[group]" in line:
            return TokenType.SECTION_START
        elif "##[endgroup]" in line:
            return TokenType.SECTION_END
        else:
            return TokenType.DEFAULT
