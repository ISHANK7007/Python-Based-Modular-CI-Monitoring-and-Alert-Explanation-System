from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple
from core.models import LogLine  # Ensure LogLine is correctly defined and imported


class TokenCategory(Enum):
    STRUCTURAL = auto()
    COMMAND = auto()
    OUTPUT = auto()
    DIAGNOSTIC = auto()
    FAILURE = auto()
    PERFORMANCE = auto()
    SYSTEM = auto()
    METADATA = auto()
    UNKNOWN = auto()


class TokenType(Enum):
    STEP = (0, TokenCategory.STRUCTURAL)
    WARNING = (50, TokenCategory.FAILURE)
    ERROR = (100, TokenCategory.FAILURE)
    INFO = (30, TokenCategory.DIAGNOSTIC)
    DEBUG = (20, TokenCategory.DIAGNOSTIC)
    SECTION_START = (0, TokenCategory.STRUCTURAL)
    SECTION_END = (0, TokenCategory.STRUCTURAL)
    COMMAND = (0, TokenCategory.COMMAND)
    STACK_TRACE = (190, TokenCategory.FAILURE)
    ASSERTION_FAIL = (150, TokenCategory.FAILURE)
    TEST_FAILURE = (160, TokenCategory.FAILURE)
    EXIT_CODE = (200, TokenCategory.FAILURE)
    DEFAULT = (0, TokenCategory.UNKNOWN)

    def __init__(self, severity: int, category: TokenCategory):
        self.severity = severity
        self.category = category

    @property
    def is_failure(self) -> bool:
        return self.category == TokenCategory.FAILURE

    @property
    def is_warning(self) -> bool:
        return 50 <= self.severity < 100

    @property
    def is_error(self) -> bool:
        return self.severity >= 100

    @classmethod
    def get_by_severity_threshold(cls, min_severity: int) -> list:
        return [t for t in cls if t.severity >= min_severity]


class SegmentType(Enum):
    STEP = "STEP"
    BLOCK = "BLOCK"
    TRACE = "TRACE"
    DEFAULT = "DEFAULT"


@dataclass
class Token:
    type: TokenType
    value: str
    line_reference: int
    source_line: LogLine
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def severity(self) -> int:
        return self.type.severity

    @property
    def category(self) -> TokenCategory:
        return self.type.category

    @property
    def is_failure(self) -> bool:
        return self.type.is_failure

    @property
    def is_warning(self) -> bool:
        return self.type.is_warning

    @property
    def is_error(self) -> bool:
        return self.type.is_error


@dataclass
class TokenizedSegment:
    segment_id: str
    tokens: List[Token]
    segment_type: SegmentType
    confidence: float
    context: Dict[str, Any]
    parent_segment_id: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    provider: Optional[str] = None
    related_segments: List[str] = field(default_factory=list)

    @property
    def span(self) -> int:
        if self.start_line is not None and self.end_line is not None:
            return self.end_line - self.start_line + 1
        return 0

    @property
    def raw_text(self) -> str:
        return "\n".join(token.value for token in self.tokens)

    @property
    def line_range(self) -> Tuple[int, int]:
        return (self.start_line or 0, self.end_line or 0)

    @property
    def severity(self) -> int:
        return max((token.severity for token in self.tokens), default=0)

    @property
    def contains_failure(self) -> bool:
        return any(token.is_failure for token in self.tokens)

    @property
    def contains_error(self) -> bool:
        return any(token.is_error for token in self.tokens)

    @property
    def contains_warning(self) -> bool:
        return any(token.is_warning for token in self.tokens)

    def get_highest_severity_tokens(self) -> List[Token]:
        max_severity = self.severity
        return [token for token in self.tokens if token.severity == max_severity]
