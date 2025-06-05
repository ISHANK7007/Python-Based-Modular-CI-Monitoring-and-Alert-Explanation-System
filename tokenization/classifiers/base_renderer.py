from datetime import datetime
from typing import Dict, Any
from core.explanation_bundle import ExplanationBundle

class BaseRenderer:
    """Base implementation of the renderer interface"""
    
    def render(self, template, data, job_context=None, verbosity=None):
        """Stub base render method to be overridden"""
        return template.render(data)  # Replace with actual logic

    def create_explanation_bundle(self, rendered_content, template, data, metadata):
        """Create an explanation bundle from rendered content"""
        return ExplanationBundle(
            summary_text=self._extract_summary(rendered_content, data),
            detailed_text=rendered_content,
            prediction_id=data.get('prediction_id', ''),
            label=data.get('label', ''),
            confidence_level=data.get('confidence', 0.0),
            confidence_category=self._get_confidence_category(data.get('confidence', 0.0)),
            format=self.format_name if hasattr(self, 'format_name') else 'markdown',
            render_style=self.render_style if hasattr(self, 'render_style') else 'default',
            verbosity_level=getattr(self, 'current_verbosity', 1),
            segments_used=self._get_segment_references() if hasattr(self, '_get_segment_references') else [],
            supporting_tokens=self._extract_supporting_tokens() if hasattr(self, '_extract_supporting_tokens') else [],
            job_context=metadata.get('job_context'),
            generation_timestamp=datetime.now().isoformat(),
            render_trace_id=getattr(self, 'trace_id', None),
            renderer_version=getattr(self, 'VERSION', '1.0'),
            template_id=getattr(template, 'template_id', 'unknown'),
            template_version=getattr(template, 'version', '1.0.0'),
            suggested_actions=self._generate_suggested_actions(data) if hasattr(self, '_generate_suggested_actions') else [],
            related_documentation=self._get_related_documentation(data) if hasattr(self, '_get_related_documentation') else [],
            interactive_elements=self._get_interactive_elements() if hasattr(self, '_get_interactive_elements') else {}
        )

    def render_with_bundle(self, template, data, job_context=None, verbosity=None):
        """Render and return an explanation bundle"""
        rendered_content = self.render(template, data, job_context, verbosity)
        return self.create_explanation_bundle(
            rendered_content, 
            template, 
            data,
            {'job_context': job_context}
        )

    def _extract_summary(self, rendered_content, data):
        return data.get("summary", "No summary available.")

    def _get_confidence_category(self, score):
        if score >= 0.8:
            return "high"
        elif score >= 0.5:
            return "medium"
        else:
            return "low"
