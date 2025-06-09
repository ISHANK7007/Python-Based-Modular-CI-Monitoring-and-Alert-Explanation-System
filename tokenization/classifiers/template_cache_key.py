from typing import Any, Dict


class DefaultTemplateCacheKeyGenerator:
    """
    Generates structured cache keys for rendered templates based on prediction metadata,
    confidence, format type, and optional template engine versioning.
    """

    def __init__(self, template_engine=None):
        self.template_engine = template_engine

    def generate_key(self, prediction: Any, format_type: str) -> str:
        """Generate a cache key for rendered templates based on prediction properties."""
        components = [
            f"tpl:{prediction.label}",
            f"provider:{prediction.metadata.get('provider', 'generic')}",
            f"conf:{self._confidence_bucket(prediction.confidence)}",
            f"fmt:{format_type}"
        ]

        # Include versioning to auto-invalidate old template entries
        if hasattr(self.template_engine, 'version'):
            components.append(f"v:{self.template_engine.version}")
        else:
            components.append("v:1")

        return "|".join(components)

    def _confidence_bucket(self, confidence: float) -> str:
        """Bucket confidence score to reduce cache key entropy and improve reuse."""
        if confidence > 0.8:
            return "high"
        elif confidence > 0.5:
            return "medium"
        else:
            return "low"
