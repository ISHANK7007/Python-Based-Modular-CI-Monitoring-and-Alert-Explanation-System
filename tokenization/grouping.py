import re
import collections
import itertools
from abc import ABC, abstractmethod
from typing import Iterator, List, Dict, Any

from tokenization.models import Token, TokenizedSegment
from tokenization.token_types import TokenType, TokenTypeSeverity
from core.models import LogLine
from tokenization.grouped_segment import GroupedSegment


# --- Grouping Strategies for TokenizedSegment -> GroupedSegment ---

class GroupingStrategy:
    """Strategy interface for grouping TokenizedSegments."""
    
    def group(self, segments: Iterator[TokenizedSegment]) -> Iterator[GroupedSegment]:
        return (GroupedSegment(
            segments=[segment],
            primary_segment=segment,
            context=segment.context.copy()
        ) for segment in segments)


class SectionBasedGrouping(GroupingStrategy):
    """Groups segments based on CI provider section markers."""
    
    def group(self, segments: Iterator[TokenizedSegment]) -> Iterator[GroupedSegment]:
        current_section = None
        buffer = []
        
        for segment in segments:
            if self._is_section_start(segment):
                if current_section and buffer:
                    yield self._create_grouped_segment(current_section, buffer)
                current_section = segment
                buffer = []
            elif self._is_section_end(segment) and current_section:
                buffer.append(segment)
                yield self._create_grouped_segment(current_section, buffer)
                current_section = None
                buffer = []
            elif current_section:
                buffer.append(segment)
            else:
                yield GroupedSegment(
                    segments=[segment], 
                    primary_segment=segment,
                    context=segment.context.copy()
                )
        
        if current_section and buffer:
            yield self._create_grouped_segment(current_section, buffer)

    def _is_section_start(self, segment: TokenizedSegment) -> bool:
        return segment.context.get("type") == "section_start"

    def _is_section_end(self, segment: TokenizedSegment) -> bool:
        return segment.context.get("type") == "section_end"

    def _create_grouped_segment(self, start_segment: TokenizedSegment, buffer: List[TokenizedSegment]) -> GroupedSegment:
        return GroupedSegment(
            segments=[start_segment] + buffer,
            primary_segment=start_segment,
            context=start_segment.context.copy()
        )
