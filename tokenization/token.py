from dataclasses import dataclass
from typing import Optional
from tokenization.segment_type import SegmentType




@dataclass
class Token:
    text: str
    line_no: int
    source: str
    section: str
