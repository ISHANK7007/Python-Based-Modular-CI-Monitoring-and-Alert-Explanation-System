
import os
import json
from ingestion.github_actions import GitHubActionsIngestor
from ingestion.gitlab import GitLabCIIngestor
from ingestion.factory import create_ingestor
from ingestion.buffered_ingestion import BufferedLogIngestor
from core.models import LogLine
from core.job_context import JobContext
from utils.metadata_injector import MetadataInjector
from utils.section_validator import SectionValidator

# Tokenization pipeline components
from tokenization.pipeline import TokenizationPipeline
from tokenization.tokenizer import BasicTokenizer as Tokenizer
from tokenization.segment_classifier import SegmentClassifier
from tokenization.context_analyzer import ContextAnalyzer
from tokenization.grouping import GroupingStrategy

# Root cause analysis engine and classifiers
from tokenization.classifiers.root_cause_engine import RootCauseAnalysisEngine
from tokenization.classifiers.rule_based_classifier import BuildFailureClassifier, OutOfMemoryClassifier, MissingDependencyClassifier

# Renderer
from tokenization.classifiers.auditable_renderer import AuditableRenderer

# Set mode
MODE = "analyze"  # Options: "gitlab", "multi", "detect", "injector", "section_validate", "tokenize", "analyze"

CLASSIFIERS = [
    BuildFailureClassifier(name="build_failure", label="BUILD_FAILURE"),
    OutOfMemoryClassifier(name="oom", label="OOM"),
    MissingDependencyClassifier(name="missing_dep", label="MISSING_DEPENDENCY")
]

def test_root_cause_analysis():
    log_path = "github_sample_log.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("2023-06-15T14:23:41.123Z Starting build\n")
        f.write("##[group]Build started\n")
        f.write("error: cannot find symbol\n")
        f.write("##[endgroup]\n")

    ingestor = GitHubActionsIngestor(log_path)
    log_lines = ingestor.stream_log(log_path)

    pipeline = TokenizationPipeline(
        tokenizer=Tokenizer(),
        segment_classifier=SegmentClassifier(classification_rules=CLASSIFIERS),
        context_analyzer=ContextAnalyzer(),
        grouping_strategy=GroupingStrategy()
    )
    segments = pipeline.process(log_lines)

    print("=== Tokenized Segments ===")
    for segment in segments:
        print(f"[Segment] ID={segment.segment_id} | Text={{segment.raw_text}} | Type={{segment.segment_type}}")

    print("\n=== Direct Match Test ===")
    build_classifier = BuildFailureClassifier(name="build_failure", label="BUILD_FAILURE")
    for s in segments:
        result = build_classifier.match(s)
        print(f"[MATCH] {{s.raw_text}} => {{result.label if result else 'No match'}}")

    engine = RootCauseAnalysisEngine(classifiers=CLASSIFIERS)
    predictions = engine.analyze(segments)

    if not predictions:
        print("No root cause predictions found.")
        os.remove(log_path)
        return

    report = engine.generate_summary_report(predictions)
    print("Summary Report:")
    print(json.dumps(report, indent=2))

    os.remove(log_path)

if __name__ == "__main__":
    if MODE == "analyze":
        test_root_cause_analysis()
