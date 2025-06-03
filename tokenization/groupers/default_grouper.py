from typing import List
from tokenization.models import TokenizedSegment

class DefaultGrouper:
    """Default grouping strategy that passes segments through unchanged."""

    def group(self, segments: List[TokenizedSegment]) -> List[TokenizedSegment]:
        # In real use, this might merge related segments.
        return segments
