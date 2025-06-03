from typing import Dict, Any, Optional
from core.explanation_bundle import ExplanationBundle
from datetime import datetime


class ExplanationBundleFactory:
    """Factory class to create ExplanationBundle objects from raw components."""

    @staticmethod
    def create(
        rendered_text: str,
        data: Dict[str, Any],
        template: Optional[Any] = None,
        job_context: Optional[Any] = None,
        trace_id: Optional[str] = None,
        renderer_version: str = "1.0.0",
        format_name: str = "markdown",
        render_style: str = "default",
        verbosity_level: str = "standard",
    ) -> ExplanationBundle:
        return ExplanationBundle(
            summary_text=rendered_text.strip().split("\n")[0],
            detailed_text=rendered_text,
            prediction_id=data.get("prediction_id", ""),
            label=data.get("label", ""),
            confidence_level=data.get("confidence", 0.0),
            confidence_category=ExplanationBundleFactory._get_confidence_category(data.get("confidence", 0.0)),
            format=format_name,
            render_style=render_style,
            verbosity_level=verbosity_level,
            segments_used=data.get("segments_used", []),
            supporting_tokens=data.get("supporting_tokens", []),
            job_context=job_context,
            generation_timestamp=datetime.utcnow().isoformat(),
            render_trace_id=trace_id,
            renderer_version=renderer_version,
            template_id=getattr(template, "template_id", "unknown"),
            template_version=getattr(template, "version", "1.0.0"),
            suggested_actions=data.get("suggested_actions", []),
            related_documentation=data.get("related_documentation", []),
            interactive_elements=data.get("interactive_elements", [])
        )

    @staticmethod
    def _get_confidence_category(confidence: float) -> str:
        if confidence > 0.8:
            return "high"
        elif confidence > 0.5:
            return "medium"
        else:
            return "low"
