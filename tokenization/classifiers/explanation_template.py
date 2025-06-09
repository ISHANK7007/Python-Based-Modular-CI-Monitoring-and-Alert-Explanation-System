from dataclasses import dataclass
from typing import List, Dict


@dataclass
class ContextSegment:
    type: str
    content: str
    relevance: float


class ExplanationTemplate:
    def __init__(self, template: str):
        self.template = template

    def render(self, data: Dict[str, str]) -> str:
        output = self.template
        for key, value in data.items():
            output = output.replace(f"{{{{{key}}}}}", value)
        return output


class MarkdownRenderer:
    def __init__(self):
        self.segments: List[ContextSegment] = []

    def with_context_segments(self, segments: List[ContextSegment]):
        self.segments = segments
        return self

    def render(self, template: ExplanationTemplate, data: Dict[str, str]) -> str:
        base_render = template.render(data)
        context_block = "\n\n### Context Segments:\n"
        for segment in self.segments:
            context_block += f"- **{segment.type}** (relevance={segment.relevance}): {segment.content}\n"
        return base_render + context_block


# Example usage
if __name__ == "__main__":
    template = ExplanationTemplate("Error occurred: {{error_summary}}")
    renderer = MarkdownRenderer()

    # Create evidence segments
    traceback_segment = ContextSegment(
        type="traceback",
        content="File 'app.py', line 42...",
        relevance=0.9
    )
    error_message = ContextSegment(
        type="error_message",
        content="IndexError: list index out of range",
        relevance=1.0
    )

    # Inject segments into renderer and render explanation
    rendered_explanation = (
        renderer
        .with_context_segments([traceback_segment, error_message])
        .render(template, {"error_summary": "List index error in main loop"})
    )

    print(rendered_explanation)
