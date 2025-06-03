from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from core.models import LogLine

# === Severity and Category Definitions ===
@dataclass(frozen=True)
class TokenTypeSeverity:
    level: int
    label: str


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


# === TokenType Definitions ===
class TokenType(Enum):
    SECTION_START = (TokenTypeSeverity(0, "info"), TokenCategory.STRUCTURAL)
    SECTION_END = (TokenTypeSeverity(0, "info"), TokenCategory.STRUCTURAL)
    COMMAND = (TokenTypeSeverity(0, "info"), TokenCategory.COMMAND)
    STACK_TRACE = (TokenTypeSeverity(190, "error"), TokenCategory.FAILURE)
    STEP = (TokenTypeSeverity(0, "info"), TokenCategory.STRUCTURAL)
    WARNING = (TokenTypeSeverity(50, "warning"), TokenCategory.FAILURE)
    ERROR = (TokenTypeSeverity(100, "error"), TokenCategory.FAILURE)
    INFO = (TokenTypeSeverity(30, "info"), TokenCategory.DIAGNOSTIC)
    DEBUG = (TokenTypeSeverity(20, "debug"), TokenCategory.DIAGNOSTIC)
    ASSERTION_FAIL = (TokenTypeSeverity(150, "error"), TokenCategory.FAILURE)
    TEST_FAILURE = (TokenTypeSeverity(160, "error"), TokenCategory.FAILURE)
    EXIT_CODE = (TokenTypeSeverity(200, "error"), TokenCategory.FAILURE)
    IGNORE = (TokenTypeSeverity(0, "info"), TokenCategory.METADATA)  # ✅ Added IGNORE token
    DEFAULT = (TokenTypeSeverity(0, "unknown"), TokenCategory.UNKNOWN)
    EXIT_CODE_NON_ZERO = (TokenTypeSeverity(201, "error"), TokenCategory.FAILURE)
    def __init__(self, severity: TokenTypeSeverity, category: TokenCategory):
        self.severity = severity
        self.category = category

    @property
    def is_failure(self) -> bool:
        return self.category == TokenCategory.FAILURE

    @property
    def is_warning(self) -> bool:
        return 50 <= self.severity.level < 100

    @property
    def is_error(self) -> bool:
        return self.severity.level >= 100

    @classmethod
    def get_by_severity_threshold(cls, min_severity: int) -> List["TokenType"]:
        return [t for t in cls if t.severity.level >= min_severity]


# === Priority Mapping ===
token_type_priorities = {
    TokenType.ERROR: 100,
    TokenType.WARNING: 90,
    TokenType.COMMAND: 80,
    # Extend as needed...
}


# === Segment Types ===
class SegmentType(Enum):
    STEP = "STEP"
    BLOCK = "BLOCK"
    TRACE = "TRACE"
    DEFAULT = "DEFAULT"


# === Token Object ===
@dataclass
class Token:
    type: TokenType
    value: str
    line_reference: int
    source_line: 'LogLine'
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def severity(self) -> int:
        return self.type.severity.level

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


# === TokenizedSegment Object ===
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
        return self.end_line - self.start_line + 1 if self.start_line is not None and self.end_line is not None else 0

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


# === Suppression Rules ===
class TokenSuppressionRule(Enum):
    """Types of token suppression rules for avoiding false positives."""
    EXACT_PHRASE = auto()
    CONTEXTUAL_PHRASE = auto()
    NEGATIVE_LOOKAHEAD = auto()
    SURROUNDING_CONTEXT = auto()
    SECTION_BASED = auto()
