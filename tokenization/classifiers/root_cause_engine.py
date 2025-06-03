from typing import List, Dict, Optional
from tokenization.classifiers.registry_core import RootCauseClassifierRegistry
from core.root_cause_prediction import RootCausePrediction
from tokenization.metrics.telemetry import TelemetryCollector
from core.root_cause_prediction_v2 import PredictionBundle


class RootCauseAnalysisEngine:
    """
    Root Cause Analysis Engine that coordinates classifier registration,
    prediction, and optional telemetry collection.
    """

    def __init__(self, classifiers: Optional[List] = None, confidence_threshold: float = 0.7, enable_telemetry: bool = False):
        self.registry = RootCauseClassifierRegistry()
        self.confidence_threshold = confidence_threshold
        self.enable_telemetry = enable_telemetry
        self.telemetry = TelemetryCollector() if enable_telemetry else None

        if classifiers:
            for classifier in classifiers:
                self.register_classifier(classifier)

    def register_classifier(self, classifier):
        """
        Register a classifier with optional telemetry wrapping.
        """
        classifier.confidence_threshold = self.confidence_threshold
        if self.enable_telemetry:
            self.telemetry.wrap_classifier(classifier)
        self.registry.register(classifier)

    def analyze(self, segments: List) -> List[RootCausePrediction]:
        """
        Perform classification on a list of tokenized segments.
        """
        predictions = self.registry.classify(segments)
        return [p for p in predictions if p.confidence >= self.confidence_threshold]

    def analyze_multi_label(self, segments: List) -> List["PredictionBundle"]:
        """
        Return multi-label prediction bundles if classifiers support it.
        """
        bundles = []
        for classifier in self.registry.classifiers.values():
            if hasattr(classifier, "classify_bundle"):
                bundles.extend(classifier.classify_bundle(segments))
        return bundles

    def get_telemetry_report(self) -> Optional[Dict]:
        """
        Return telemetry report if telemetry is enabled.
        """
        if not self.enable_telemetry:
            return None
        return self.telemetry.generate_report()

    def generate_summary_report(self, predictions: List[RootCausePrediction]) -> dict:
        """
        Generate a traceable, human-readable summary report from root cause predictions.

        Args:
            predictions: List of RootCausePrediction instances

        Returns:
            Structured summary dictionary
        """
        if not predictions:
            return {"status": "no_issues", "all_issues": []}

        # Find primary issue: highest confidence
        primary = max(predictions, key=lambda p: p.confidence)

        trace_urls = []
        all_issues = []
        affected_jobs = set()
        affected_sections = set()

        for pred in predictions:
            refs = []
            for ref in getattr(pred, "references", []):
                affected_jobs.add(ref.get("job_id", ""))
                affected_sections.add(ref.get("section", ""))
                refs.append(ref)
                trace_urls.append({
                    "label": pred.label,
                    "url": ref.get("url"),
                    "context": {
                        "job_id": ref.get("job_id"),
                        "section": ref.get("section"),
                        "line_range": ref.get("line_range")
                    }
                })

            all_issues.append({
                "label": pred.label,
                "confidence": pred.confidence,
                "references": refs
            })

        return {
            "status": "issues_detected",
            "primary_issue": {
                "label": primary.label,
                "confidence": primary.confidence,
                "description": getattr(primary, "description", ""),
                "evidence": getattr(primary, "supporting_tokens", [])
            },
            "affected_jobs": sorted(affected_jobs),
            "affected_sections": sorted(affected_sections),
            "all_issues": all_issues,
            "trace_urls": trace_urls
        }
