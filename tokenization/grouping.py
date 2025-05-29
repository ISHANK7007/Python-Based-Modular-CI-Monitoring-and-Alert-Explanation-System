from typing import Iterator, List
from tokenization.models import TokenizedSegment
from tokenization.grouped_segment import GroupedSegment

class GroupingStrategy:
    """Strategy interface for grouping TokenizedSegments."""
    
    def group(self, segments: Iterator[TokenizedSegment]) -> Iterator[GroupedSegment]:
        """Group segments according to the strategy."""
        raise NotImplementedError

class SectionBasedGrouping(GroupingStrategy):
    """Groups segments based on CI provider section markers."""
    
    def group(self, segments: Iterator[TokenizedSegment]) -> Iterator[GroupedSegment]:
        current_section = None
        buffer = []
        
        for segment in segments:
            if self._is_section_start(segment):
                # Yield the previous section if it exists
                if current_section and buffer:
                    yield self._create_grouped_segment(current_section, buffer)
                
                # Start a new section
                current_section = segment
                buffer = []
            elif self._is_section_end(segment) and current_section:
                # Add this end marker to the buffer
                buffer.append(segment)
                
                # Yield the completed section
                yield self._create_grouped_segment(current_section, buffer)
                
                # Reset tracking
                current_section = None
                buffer = []
            elif current_section:
                # Add to current section's buffer
                buffer.append(segment)
            else:
                # No active section, yield as standalone
                yield GroupedSegment(
                    segments=[segment], 
                    primary_segment=segment,
                    context=segment.context.copy()
                )
        
        # Handle any remaining buffered segments
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

class CommandOutputGrouping(GroupingStrategy):
    """Groups command execution with its output and result."""
    
    def group(self, segments: Iterator[TokenizedSegment]) -> Iterator[GroupedSegment]:
        # Implementation that groups command lines with their output
        pass
