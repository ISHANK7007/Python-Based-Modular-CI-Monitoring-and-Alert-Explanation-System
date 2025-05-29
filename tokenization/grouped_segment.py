from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from typing import Dict, Any, Iterator, List, Optional
from tokenization.models import TokenizedSegment

@dataclass
class GroupedSegment:
    """A group of related TokenizedSegments with a primary segment and context."""
    
    segments: List[TokenizedSegment]
    primary_segment: TokenizedSegment
    context: Dict[str, Any] = field(default_factory=dict)
    scope: Optional[str] = None

    @property
    def line_range(self) -> Tuple[int, int]:
        """Get the line range covered by all segments in this group."""
        start = min(segment.line_range[0] for segment in self.segments)
        end = max(segment.line_range[1] for segment in self.segments)
        return (start, end)

    @property
    def raw_text(self) -> str:
        """Get the combined raw text of all segments."""
        return "\n".join(segment.raw_text for segment in self.segments)
