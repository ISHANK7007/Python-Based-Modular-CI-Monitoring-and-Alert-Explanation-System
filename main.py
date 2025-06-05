
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ingestion.github_actions import GitHubActionsIngestor
from core.feedback_processor import FeedbackProcessor
from core.feedback_governance import FeedbackGovernance, ReviewLevel
from core.validation_response import ValidationResponse
from utils.feedback_validator import FeedbackValidator
from utils.metadata_injector import MetadataInjector
from utils.section_validator import SectionValidator

from tokenization.pipeline import TokenizationPipeline
from tokenization.tokenizer import BasicTokenizer as Tokenizer
from tokenization.segment_classifier import SegmentClassifier
from tokenization.context_analyzer import ContextAnalyzer
from tokenization.grouping import GroupingStrategy

from tokenization.classifiers.root_cause_engine import RootCauseAnalysisEngine
from tokenization.classifiers.rule_based_classifier import (
    BuildFailureClassifier,
    OutOfMemoryClassifier,
    MissingDependencyClassifier,
)
from tokenization.classifiers.template_adjustment_middleware import TemplateAdjustmentMiddleware
from tokenization.classifiers.feedback_aware_renderer import FeedbackAwareRenderer
from tokenization.classifiers.auditable_renderer import AuditableRenderer
from tokenization.classifiers.bundle_factory import ExplanationBundleFactory
from tokenization.classifiers.template_cache_key import DefaultTemplateCacheKeyGenerator

class DummyValidator:
    def validate(self, feedback):
        return type("ValidationResult", (), {"valid": True, "warnings": [], "stage": "validated"})()

class DummyAdjuster:
    def adjust(self, feedback, instructions): return feedback

class DummyChecker:
    def check(self, feedback): return type("Result", (), {"valid": True, "severity": "low", "warnings": [], "stage": "adjusted"})()

class DummyImpact:
    def analyze(self, feedback): return type("Impact", (), {"risk_score": 0.2, "details": {}, "regression_detected": False})()

class DummyLogger:
    def log(self, x): print("[Warning]", x)

def test_pipeline_with_feedback():
    log_path = "sample_log.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("2023-06-15T14:23:41.123Z Starting build\n")
        f.write("##[group]Build started\n")
        f.write("error: cannot find symbol\n")
        f.write("##[endgroup]\n")

    ingestor = GitHubActionsIngestor(log_path)
    log_lines = ingestor.stream_log(log_path)

    CLASSIFIERS = [
        BuildFailureClassifier(name="build_failure", label="BUILD_FAILURE"),
        OutOfMemoryClassifier(name="oom", label="OOM"),
        MissingDependencyClassifier(name="missing_dep", label="MISSING_DEPENDENCY"),
    ]

    pipeline = TokenizationPipeline(
        tokenizer=Tokenizer(),
        segment_classifier=SegmentClassifier(classification_rules=CLASSIFIERS),
        context_analyzer=ContextAnalyzer(),
        grouping_strategy=GroupingStrategy(),
    )

    segments = list(pipeline.process(log_lines))
    print("\n=== Segments ===")
    for s in segments:
        print(f"[Segment] {s.segment_id} | {s.raw_text}")

    engine = RootCauseAnalysisEngine(classifiers=CLASSIFIERS)
    predictions = engine.analyze(segments)
    report = engine.generate_summary_report(predictions)
    print("\n=== Root Cause Summary ===")
    print(json.dumps(report, indent=2))

    feedback_event = {
        "original_prediction": predictions[0].label if predictions else "BUILD_FAILURE",
        "corrected_label": "VERSION_MISMATCH",
        "job_id": "job_123",
        "segment_id": segments[0].segment_id if segments else "s1"
    }

    processor = FeedbackProcessor(
        syntactic_validator=DummyValidator(),
        semantic_validator=DummyValidator(),
        feedback_adjuster=DummyAdjuster(),
        consistency_checker=DummyChecker(),
        impact_analyzer=DummyImpact(),
        config=type("Config", (), {"risk_threshold": 0.5})(),
        warning_logger=DummyLogger()
    )

    result = processor.process_feedback(feedback_event)
    print("\n=== Feedback Validation Result ===")
    print(f"Valid: {result.valid}, Stage: {result.stage}")

    middleware = TemplateAdjustmentMiddleware()
    bundle_factory = ExplanationBundleFactory()
    telemetry_logger = lambda x: print("[Telemetry]", x)

    auditable_renderer = AuditableRenderer(debug_level=2)

    renderer = FeedbackAwareRenderer(
        base_renderer=auditable_renderer,
        template_adjustment_middleware=middleware
    )

    if segments:
        explanation = renderer.render(
            template="Root cause: {{segment.summary}}",
            context={
                "job_id": "job_123",
                "segment_id": segments[0].segment_id,
                "segment_type": segments[0].segment_type,
                "segment": segments[0]
            }
        )
        print("\n=== Final Rendered Output ===")
        print(explanation)

    os.remove(log_path)

if __name__ == "__main__":
    test_pipeline_with_feedback()
