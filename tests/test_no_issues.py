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
from tokenization.grouping import SectionBasedGrouping
from tokenization.classifiers.rule_based_classifier import BuildFailureClassifier, OutOfMemoryClassifier

def test_no_issues_log():
    log_path = os.path.join(PROJECT_ROOT, "logs", "test_no_issues_log.txt")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("2023-06-15T14:23:41.123Z Starting build\n")
        f.write("Build completed successfully.\n")

    # Step 1: Ingest log
    ingestor = GitHubActionsIngestor(log_path)
    log_lines = ingestor.stream_log(log_path)

    # Step 2: Construct pipeline
    segment_classifier = SegmentClassifier(classification_rules=[
        BuildFailureClassifier(name="build_failure", label="BUILD_FAILURE"),
        OutOfMemoryClassifier(name="oom", label="OOM")
    ])

    pipeline = TokenizationPipeline(
        tokenizer=BasicTokenizer(),
        segment_classifier=segment_classifier,
        context_analyzer=ContextAnalyzer(),
        grouping_strategy=SectionBasedGrouping()
    )

    # Step 3: Run tokenization pipeline
    segments = pipeline.process(log_lines)

    print("=== Segments ===")
    for i, seg in enumerate(segments, 1):
        raw_text = seg.tokens[0].value if seg.tokens else "N/A"
        print(f"Segment {i}:")
        print(f"  ID: {getattr(seg, 'segment_id', 'N/A')}")
        print(f"  Type: {getattr(seg, 'segment_type', 'N/A')}")
        print(f"  Raw Text: {raw_text.strip()}")
        print(f"  Classification: {seg.context.get('classification')}")
        print(f"  Confidence: {seg.context.get('confidence')}")
        print("-" * 40)

    # Step 4: Analyze root cause
    engine = RootCauseAnalysisEngine()
    for clf in segment_classifier.get_classifiers():
        engine.register_classifier(clf)

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

if __name__ == "__main__":
    test_no_issues_log()
