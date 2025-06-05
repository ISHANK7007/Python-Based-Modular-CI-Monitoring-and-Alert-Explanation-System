from typing import List, Dict, Optional
from dataclasses import dataclass


# Placeholder interface for the renderer
class ITemplateRenderer:
    def render(self, template, data):
        raise NotImplementedError


@dataclass
class SegmentReference:
    section: Optional[str]
    line_range: tuple


@dataclass
class ContextSegment:
    segment_id: str
    type: str
    content: str
    relevance: float
    supporting_tokens: List[str]


class MarkdownRenderer(ITemplateRenderer):
    def with_context_segments(self, segments: List[ContextSegment], references: Dict[str, SegmentReference]):
        self.segments = segments
        self.segment_references = references  # Map of segment_ids to SegmentReference objects
        return self

    def highlight_tokens(self, content: str, tokens: List[str]) -> str:
        """Apply markdown bold formatting to specified tokens"""
        for token in sorted(set(tokens), key=len, reverse=True):  # Longer tokens first
            content = content.replace(token, f"**{token}**")
        return content

    def render_relevant_context(self) -> str:
        """Generate a 'Relevant Log Context' section with highlighted evidence"""
        context_section = "## Relevant Log Context\n\n"
        for segment in self.segments:
            ref = self.segment_references.get(segment.segment_id)
            if not ref:
                continue

            section_name = ref.section or 'Log Section'
            line_info = f"(lines {ref.line_range[0]}–{ref.line_range[1]})"

            context_section += f"### {section_name} {line_info}\n"
            context_section += "```\n"
            context_section += self.highlight_tokens(segment.content, segment.supporting_tokens)
            context_section += "\n```\n"
            context_section += f"*Relevance: {segment.relevance:.2f}*\n\n"
        return context_section


# Example usage
if __name__ == "__main__":
    segments = [
        ContextSegment(
            segment_id="s1",
            type="error",
            content="Error: Null pointer exception at line 17",
            relevance=0.95,
            supporting_tokens=["Null pointer", "line 17"]
        )
    ]

    references = {
        "s1": SegmentReference(section="Build Log", line_range=(15, 20))
    }

    renderer = MarkdownRenderer()
    result = renderer.with_context_segments(segments, references).render_relevant_context()
    print(result)
