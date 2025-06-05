from typing import List, Dict


# Sample fallback templates
FALLBACK_TEMPLATES = {
    "generic": "The failure was likely caused by an unknown issue in the {{environment_type}} environment.",
    "environment": "The failure was likely due to instability in the {{environment_type}} environment.",
    "timeout": "The job appears to have timed out. This could be due to resource constraints or delays.",
}


class BaseRenderer:
    def handle_low_confidence(self, prediction, segments):
        """Generate appropriate content for low-confidence or fallback cases"""
        template_type = prediction.metadata.get('fallback_type', 'generic')
        template = FALLBACK_TEMPLATES.get(template_type, FALLBACK_TEMPLATES['generic'])

        # Format the template with available context
        context = {
            'environment_type': prediction.metadata.get('environment_type', 'CI'),
            'confidence': f"{prediction.confidence:.2f}",
            # Add more fields if needed
        }

        explanation = self._format_template(template, context)
        disclaimer = self._format_confidence_disclaimer(prediction.confidence)
        annotated_segments = self._format_potential_evidence(segments)
        suggestions = self._generate_troubleshooting_suggestions(template_type)

        return {
            'explanation': explanation,
            'disclaimer': disclaimer,
            'potential_evidence': annotated_segments,
            'suggestions': suggestions
        }

    def _format_template(self, template: str, context: Dict[str, str]) -> str:
        for key, val in context.items():
            template = template.replace(f"{{{{{key}}}}}", val)
        return template

    def _format_confidence_disclaimer(self, confidence: float) -> str:
        """Create an appropriate disclaimer based on confidence level"""
        if confidence < 0.3:
            return "This explanation has **very low confidence**. Multiple factors may be contributing to the failure."
        elif confidence < 0.5:
            return "This explanation has **low confidence**. Consider it as one possible interpretation of the failure."
        else:
            return "This explanation has **moderate confidence** but may not capture all contributing factors."

    def _format_potential_evidence(self, segments: List[str]) -> List[str]:
        """Stub: return summary of segments (e.g., error traces or log lines)"""
        return [f"- Evidence: {s}" for s in segments] if segments else ["- No direct evidence available."]

    def _generate_troubleshooting_suggestions(self, template_type: str) -> List[str]:
        if template_type == "environment":
            return ["Check recent changes to environment configs.", "Retry the job with increased resource limits."]
        elif template_type == "timeout":
            return ["Review long-running steps.", "Increase timeout settings in your CI configuration."]
        return ["Investigate logs for unusual patterns.", "Rerun with debug mode enabled."]


# Example usage
class MockPrediction:
    def __init__(self, confidence, metadata):
        self.confidence = confidence
        self.metadata = metadata


if __name__ == "__main__":
    prediction = MockPrediction(
        confidence=0.42,
        metadata={"fallback_type": "environment", "environment_type": "staging"}
    )
    renderer = BaseRenderer()
    result = renderer.handle_low_confidence(prediction, segments=["Database connection reset", "Job exited early"])
    for key, val in result.items():
        print(f"{key}:\n{val}\n")
