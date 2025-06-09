from dataclasses import dataclass, field
from typing import List, Any
from tokenization.segment_type import SegmentType

@dataclass
class Segment:
    start_line: int
    end_line: int
    segment_type: SegmentType
    label: str
    lines: List[Any]
    metadata: dict = field(default_factory=dict)

    @property
    def summary(self) -> str:
        return self.lines[0].raw_text if self.lines else ""
