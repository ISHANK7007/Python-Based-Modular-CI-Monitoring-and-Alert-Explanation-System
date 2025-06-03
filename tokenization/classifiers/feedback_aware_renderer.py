# tokenization/classifiers/feedback_aware_renderer.py

from tokenization.classifiers.renderer_interface import ITemplateRenderer


class FeedbackAwareRenderer(ITemplateRenderer):
    """
    Renderer wrapper that integrates feedback-based corrections
    into the rendering pipeline via middleware.
    """

    def __init__(self, base_renderer, template_adjustment_middleware):
        self.base_renderer = base_renderer
        self.middleware = template_adjustment_middleware

    def render(self, template, context):
        """
        Applies feedback-based template corrections before rendering.
        
        Args:
            template (str): The original template string.
            context (dict): The rendering context with job and label info.

        Returns:
            str: The final rendered explanation.
        """
        adjusted_template = self.middleware.process_template(
            template,
            context,
            self._extract_metadata(context)
        )
        return self.base_renderer.render(adjusted_template, context)

    def _extract_metadata(self, context):
        """
        Extracts metadata needed for feedback alignment.

        Args:
            context (dict): The full rendering context.

        Returns:
            Namespace-like metadata object (job_id, segment_id, etc.)
        """
        return type("Metadata", (), {
            "job_id": context.get("job_id"),
            "segment_id": context.get("segment_id"),
            "segment_type": context.get("segment_type")
        })()
