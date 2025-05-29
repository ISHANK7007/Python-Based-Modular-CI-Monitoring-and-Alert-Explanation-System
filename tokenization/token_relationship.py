from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class Token:
    type: str
    value: str
    line_reference: int
    source_line: Any
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TokenizedSegment:
    segment_id: str
    tokens: list
    segment_type: str
    confidence: float
    context: dict
    parent_segment_id: str = None
    start_line: int = None
    end_line: int = None
    provider: str = None
    related_segments: list = field(default_factory=list)

    @property
    def raw_text(self):
        return "\n".join(token.value for token in self.tokens)

    @property
    def line_range(self):
        return (self.start_line or 0, self.end_line or 0)

@dataclass
class TokenRelationship:
    source_token: Token
    target_token: Token
    relationship_type: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
