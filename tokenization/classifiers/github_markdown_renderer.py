from typing import List, Dict
from dataclasses import dataclass


@dataclass
class ContextSegment:
    segment_id: str
    type: str
    content: str
    relevance: float
    supporting_tokens: List[str]


class MarkdownRenderer:
    def __init__(self):
        self.segments: List[ContextSegment] = []
        self.segment_references: Dict[str, any] = {}

    def with_context_segments(self, segments: List[ContextSegment], references: Dict[str, any]):
        self.segments = segments
        self.segment_references = references
        return self

    def highlight_tokens(self, content: str, tokens: List[str]) -> str:
        """Apply markdown bold formatting to specified tokens"""
        for token in sorted(set(tokens), key=len, reverse=True):
            content = content.replace(token, f"**{token}**")
        return content

    def render_relevant_context(self) -> str:
        """Generate a 'Relevant Log Context' section with highlighted evidence"""
        context_section = "## Relevant Log Context\n\n"
        for segment in self.segments:
            ref = self.segment_references.get(segment.segment_id)
            if not ref:
                continue
            section = getattr(ref, 'section', 'Log Section')
            lines = getattr(ref, 'line_range', (0, 0))
            context_section += f"### {section} (lines {lines[0]}–{lines[1]})\n"
            context_section += "```\n"
            context_section += self.highlight_tokens(segment.content, segment.supporting_tokens)
            context_section += "\n```\n"
            context_section += f"*Relevance: {segment.relevance:.2f}*\n\n"
        return context_section


class GitHubMarkdownRenderer(MarkdownRenderer):
    """Specialized renderer for GitHub issue comments and PR reviews"""

    MAX_VISIBLE_LINES = 8
    MAX_SEGMENTS = 3  # Initial visible segments

    def format_confidence(self, confidence: float) -> str:
        """Format confidence score as GitHub-compatible badge"""
        if confidence > 0.8:
            return "![High Confidence](https://img.shields.io/badge/confidence-high-success)"
        elif confidence > 0.5:
            return "![Medium Confidence](https://img.shields.io/badge/confidence-medium-yellow)"
        else:
            return "![Low Confidence](https://img.shields.io/badge/confidence-low-critical)"

    def create_collapsible_section(self, title: str, content: str, initially_open: bool = False) -> str:
        """Create a collapsible <details> section for GitHub markdown"""
        open_attr = " open" if initially_open else ""
        return (
            f"<details{open_attr}>\n"
            f"<summary>{title}</summary>\n\n"
            f"{content.strip()}\n\n"
            f"</details>\n"
        )

    def sanitize_for_github(self, content: str) -> str:
        """Escape special markdown characters"""
        return content.replace('<', '&lt;').replace('>', '&gt;')

    def format_log_excerpt(self, segment: ContextSegment, highlight_tokens: List[str] = None) -> str:
        content = self.sanitize_for_github(segment.content)
        lines = content.split('\n')

        if len(lines) > self.MAX_VISIBLE_LINES:
            visible = "\n".join(lines[:self.MAX_VISIBLE_LINES])
            content = f"{visible}\n...\n(+{len(lines) - self.MAX_VISIBLE_LINES} more lines)"

        if highlight_tokens:
            for token in sorted(set(highlight_tokens), key=len, reverse=True):
                content = content.replace(token, f"**{token}**")

        return f"```\n{content.strip()}\n```"

    def render_segment_summary(self, segment: ContextSegment, confidence_score: float) -> str:
        badge = self.format_confidence(confidence_score)
        excerpt = self.format_log_excerpt(segment, segment.supporting_tokens)
        return f"{badge}\n\n{excerpt}"


# Optional: demo block
if __name__ == "__main__":
    segment = ContextSegment(
        segment_id="s1",
        type="error",
        content="Traceback (most recent call last):\n  File 'main.py', line 10",
        relevance=0.92,
        supporting_tokens=["Traceback", "main.py"]
    )
    ref = type("Ref", (), {"section": "Build", "line_range": (9, 12)})
    renderer = GitHubMarkdownRenderer()
    result = (
        renderer
        .with_context_segments([segment], {"s1": ref})
        .render_relevant_context()
    )
    print(result)
