from datetime import datetime
from typing import Dict, Any

from tokenization.classifiers.renderer_interface import ITemplateRenderer
from core.explanation_bundle import ExplanationBundle  # Adjust if located elsewhere


class BaseRenderer(ITemplateRenderer):
    """Base implementation of the renderer interface"""

    VERSION = "1.0.0"
    format_name = "markdown"
    render_style = "default"
    current_verbosity = ITemplateRenderer.STANDARD

    def render_with_bundle(self, template, data: Dict[str, Any], job_context=None, verbosity=None) -> ExplanationBundle:
        """Render and return an explanation bundle"""
        rendered_content = self.render(template, data, job_context, verbosity)
        return self.create_explanation_bundle(
            rendered_content,
            template,
            data,
            {'job_context': job_context}
        )

    def create_explanation_bundle(self, rendered_content: str, template, data: Dict[str, Any], metadata: Dict[str, Any]) -> ExplanationBundle:
        """Create an explanation bundle from rendered content"""
        return ExplanationBundle(
            summary_text=self._extract_summary(rendered_content, data),
            detailed_text=rendered_content,
            prediction_id=data.get('prediction_id', ''),
            label=data.get('label', ''),
            confidence_level=data.get('confidence', 0.0),
            confidence_category=self._get_confidence_category(data.get('confidence', 0.0)),
            format=self.format_name,
            render_style=self.render_style,
            verbosity_level=self.current_verbosity,
            segments_used=self._get_segment_references(),
            supporting_tokens=self._extract_supporting_tokens(),
            job_context=metadata.get('job_context'),
            generation_timestamp=datetime.now().isoformat(),
            render_trace_id=getattr(self, 'trace_id', None),
            renderer_version=self.VERSION,
            template_id=getattr(template, 'template_id', 'unknown'),
            template_version=getattr(template, 'version', '1.0.0'),
            suggested_actions=self._generate_suggested_actions(data),
            related_documentation=self._get_related_documentation(data),
            interactive_elements=self._get_interactive_elements()
        )

    # --- Stubbed helper methods below ---

    def _extract_summary(self, rendered_content: str, data: Dict[str, Any]) -> str:
        return rendered_content.split("\n")[0].strip()

    def _get_confidence_category(self, confidence: float) -> str:
        if confidence > 0.8:
            return "high"
        elif confidence > 0.5:
            return "medium"
        else:
            return "low"

    def _get_segment_references(self):
        return getattr(self, 'active_segments', [])

    def _extract_supporting_tokens(self):
        return []

    def _generate_suggested_actions(self, data: Dict[str, Any]):
        return []

    def _get_related_documentation(self, data: Dict[str, Any]):
        return []

    def _get_interactive_elements(self):
        return []
