import sys
import os

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from tokenization.pipeline import TokenizationPipeline
from ingestion.github_actions import GitHubActionsIngestor
from core.root_cause_prediction_v2 import RootCauseAnalysisEngine
from tokenization.tokenizer import BasicTokenizer
from tokenization.segment_classifier import SegmentClassifier
from tokenization.context_analyzer import ContextAnalyzer
from tokenization.grouping import GroupingStrategy
from tokenization.classifiers.rule_based_classifier import BuildFailureClassifier, OutOfMemoryClassifier

def test_with_build_error_log():
    log_path = os.path.join(PROJECT_ROOT, "logs", "test_with_build_error_log.txt")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("Starting build step\n")
        f.write("Compiling modules...\n")
        f.write("error: cannot find symbol\n")
        f.write("  symbol:   variable myVar\n")
        f.write("  location: class MyClass\n")

    ingestor = GitHubActionsIngestor(log_path)
    log_lines = ingestor.stream_log(log_path)

    build_failure = BuildFailureClassifier(name="build_failure", label="BUILD_FAILURE")
    oom_failure = OutOfMemoryClassifier(name="oom", label="OOM")

    for clf in [build_failure, oom_failure]:
        if not hasattr(clf, "classifier_id"):
            clf.classifier_id = clf.name

    segment_classifier = SegmentClassifier(classification_rules=[build_failure, oom_failure])

    pipeline = TokenizationPipeline(
        tokenizer=BasicTokenizer(),
        segment_classifier=segment_classifier,
        context_analyzer=ContextAnalyzer(),
        grouping_strategy=GroupingStrategy()
    )
    segments = pipeline.process(log_lines)

    print("=== Segments ===")
    for i, seg in enumerate(segments, 1):
        raw_text = seg.raw_text.strip() if hasattr(seg, "raw_text") else "N/A"
        print(f"Segment {i}:")
        print(f"  ID: {getattr(seg, 'segment_id', 'N/A')}")
        print(f"  Type: {getattr(seg, 'segment_type', 'N/A')}")
        print(f"  Raw Text: {raw_text}")
        print(f"  Classification: {seg.context.get('classification')}")
        print(f"  Confidence: {seg.context.get('confidence')}")
        print("-" * 40)

    engine = RootCauseAnalysisEngine()
    engine.register_classifier(build_failure)
    engine.register_classifier(oom_failure)

    predictions = engine.analyze(segments)

    print("\n=== Predictions ===")
    if not predictions:
        print("No root cause predictions.")
    else:
        for pred in predictions:
            print(f"Label: {pred.label}")
            print(f"Confidence: {pred.confidence}")
            print(f"Segment IDs: {pred.segment_ids}")
            print("-" * 40)

    assert any(p.label == "BUILD_FAILURE" for p in predictions),         f"No BUILD_FAILURE found. Predictions: {[p.label for p in predictions]}"

if __name__ == "__main__":
    test_with_build_error_log()
