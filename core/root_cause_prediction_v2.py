from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from tokenization.classifiers.registry_core import RootCauseClassifierRegistry
from tokenization.metrics.telemetry import TelemetryCollector

@dataclass
class RootCausePrediction:
    label: str
    confidence: float
    segment_ids: List[str]
    supporting_tokens: List[str] = field(default_factory=list)
    provider_context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    classifier_id: Optional[str] = None
    references: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class PredictionBundle:
    classifier_name: str
    predictions: List[RootCausePrediction] = field(default_factory=list)
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class RootCauseAnalysisEngine:
    def __init__(self, confidence_threshold: float = 0.7, enable_telemetry: bool = False):
        self.registry = RootCauseClassifierRegistry()
        self.confidence_threshold = confidence_threshold
        self.enable_telemetry = enable_telemetry
        self.telemetry = TelemetryCollector() if enable_telemetry else None

    def register_classifier(self, classifier):
        classifier.confidence_threshold = self.confidence_threshold
        if self.enable_telemetry:
            self.telemetry.wrap_classifier(classifier)
        self.registry.register(classifier)

    def analyze(self, segments: List) -> List[RootCausePrediction]:
        predictions = self.registry.classify(segments)
        return [p for p in predictions if p.confidence >= self.confidence_threshold]

    def analyze_multi_label(self, segments: List) -> List[PredictionBundle]:
        bundles = []
        for classifier in self.registry.classifiers.values():
            if hasattr(classifier, "classify_bundle"):
                bundles.extend(classifier.classify_bundle(segments))
        return bundles

    def get_telemetry_report(self) -> Optional[Dict]:
        if not self.enable_telemetry:
            return None
        return self.telemetry.generate_report()

    def generate_summary_report(self, predictions: List[RootCausePrediction]) -> dict:
        if not predictions:
            return {"status": "no_issues", "all_issues": []}

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
