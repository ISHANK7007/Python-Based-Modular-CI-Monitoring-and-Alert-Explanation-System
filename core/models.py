from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
import datetime
import json
from uuid import uuid4
from tokenization.token_types import TokenType

# === LogLine ===
@dataclass
class LogLine:
    timestamp: Optional[datetime.datetime]
    level: str
    message: str
    source: str
    raw_content: str

    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_timestamp: Optional[str] = None

    step_name: Optional[str] = None
    section: Optional[str] = None
    job_id: Optional[str] = None
    workflow_name: Optional[str] = None

    section_path: List[str] = field(default_factory=list)
    section_level: int = 0

    stream_type: str = "stdout"
    content_type: str = "log"
    is_structural: bool = False

    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    span: Optional[Dict[str, int]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "level": self.level,
            "message": self.message,
            "source": self.source,
            "raw_content": self.raw_content,
            "metadata": self.metadata,
            "raw_timestamp": self.raw_timestamp,
            "step_name": self.step_name,
            "section": self.section,
            "job_id": self.job_id,
            "workflow_name": self.workflow_name,
            "section_path": self.section_path,
            "section_level": self.section_level,
            "stream_type": self.stream_type,
            "content_type": self.content_type,
            "is_structural": self.is_structural,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column": self.column,
            "span": self.span,
        }
        return {k: v for k, v in result.items() if v is not None}

    def to_json(self, indent: Optional[int] = None) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LogLine':
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.datetime.fromisoformat(data["timestamp"])
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'LogLine':
        return cls.from_dict(json.loads(json_str))

    def get_full_section_path(self, separator: str = " > ") -> str:
        if not self.section_path:
            return ""
        return separator.join(self.section_path)

    def has_error_indicators(self) -> bool:
        return (
            self.level in ("error", "fatal") or
            self.stream_type == "stderr" or
            "error" in self.message.lower() or
            "exception" in self.message.lower() or
            "fail" in self.message.lower()
        )

    def get_context_summary(self) -> str:
        parts = []
        ts = self.timestamp.isoformat() if self.timestamp else "no-timestamp"
        summary = f"[{self.level.upper()}] {ts}"

        if self.message:
            summary += f" | {self.message}"

        if self.workflow_name:
            parts.append(f"Workflow: {self.workflow_name}")
        if self.job_id:
            parts.append(f"Job: {self.job_id}")
        if self.step_name:
            parts.append(f"Step: {self.step_name}")
        if self.section:
            parts.append(f"Section: {self.section}")
        elif self.section_path:
            parts.append(f"Section: {self.get_full_section_path()}")

        if self.file_path:
            loc = self.file_path
            if self.line_number:
                loc += f":{self.line_number}"
                if self.column:
                    loc += f":{self.column}"
            parts.append(f"Location: {loc}")

        if parts:
            summary += " | " + " | ".join(parts)
        return summary

# === Token ===
@dataclass
class Token:
    type: TokenType
    value: str
    line_reference: int
    source_line: LogLine
    metadata: Dict[str, Any] = field(default_factory=dict)
    structural_context: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.source_line and not self.structural_context:
            self.structural_context = {
                'section': self.source_line.section,
                'stream_type': self.source_line.stream_type,
                'step_name': self.source_line.step_name,
                'job_id': self.source_line.job_id
            }

    @property
    def section(self) -> Optional[str]:
        return self.structural_context.get('section') or self.source_line.section

    @property
    def stream_type(self) -> Optional[str]:
        return self.structural_context.get('stream_type') or self.source_line.stream_type

    @property
    def step_name(self) -> Optional[str]:
        return self.structural_context.get('step_name') or self.source_line.step_name

    @property
    def job_id(self) -> Optional[str]:
        return self.structural_context.get('job_id') or self.source_line.job_id

    def crosses_boundary_with(self, other_token: 'Token') -> Optional[str]:
        if self.section != other_token.section:
            return 'SECTION'
        if self.stream_type != other_token.stream_type:
            return 'STREAM'
        if self.step_name != other_token.step_name:
            return 'STEP'
        if self.job_id != other_token.job_id:
            return 'JOB'
        return None

# === TokenizedSegment ===
@dataclass
class TokenizedSegment:
    tokens: List[Token]
    raw_text: str
    line_range: Tuple[int, int]

    id: str = field(default_factory=lambda: str(uuid4()))
    context: Dict[str, Any] = field(default_factory=dict)
    scope: Optional[str] = None
    segment_score: float = 0.0
    section_context: Optional[str] = None
    provider: Optional[str] = None
    confidence_level: float = 1.0
    token_distribution: Dict[TokenType, int] = field(default_factory=dict)
    entropy: float = 0.0

# === ContextualSegment ===
@dataclass
class ContextualSegment(TokenizedSegment):
    context_clues: List[Any] = field(default_factory=list)
    related_segments: List[int] = field(default_factory=list)
    is_continuation: bool = False
    context_start_line: Optional[int] = None
    parent_context: Optional[str] = None
