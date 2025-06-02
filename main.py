import os
import json
from ingestion.github_actions import GitHubActionsIngestor
from ingestion.gitlab import GitLabCIIngestor
from ingestion.factory import create_ingestor
from ingestion.buffered_ingestion import BufferedLogIngestor
from core.models import LogLine
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
from tokenization.classifiers.rule_based_classifier import BuildFailureClassifier, OutOfMemoryClassifier

MODE = "analyze"  # Options: "gitlab", "multi", "detect", "injector", "section_validate", "tokenize", "analyze"

# ✅ Corrected instantiation with required arguments: name and label
CLASSIFIERS = [
    BuildFailureClassifier(name="build_failure", label="BUILD_FAILURE"),
    OutOfMemoryClassifier(name="oom", label="OOM")
]

def test_gitlab_streaming():
    log_path = "gitlab_sample_log.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("section_start:1716816585:setup[collapsed=true]\n")
        f.write("2023-06-15T14:23:41.123Z Initializing environment\n")
        f.write("section_end:1716816590:setup\n")
        f.write("2023-06-15T14:23:42.456Z Running build step\n")
        f.write("2023-06-15T14:23:43.789Z Compilation successful\n")

    ingestor = GitLabCIIngestor(log_path)
    for log in ingestor.stream_log():
        print(f"[{log.timestamp}] [{log.level.upper()}] {log.message} | metadata: {log.metadata}")
    print("\nSection Structure:")
    print(ingestor.get_section_structure())
    os.remove(log_path)

def test_multi_source_streaming():
    sources = [
        {"path": "gitlab_sample_log.txt", "type": "gitlab"},
        {"path": "github_sample_log.txt", "type": "github"},
    ]
    ingestor = BufferedLogIngestor(sources)
    for log in ingestor.stream_log():
        print(f"[{log.timestamp}] [{log.level.upper()}] {log.message}")

def test_auto_detection():
    log_path = "github_sample_log.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("2023-06-15T14:23:41.123Z Starting build\n")
        f.write("##[warning] Deprecated API usage\n")
        f.write("2023-06-15T14:23:42.456Z Build step completed\n")

    with open(log_path, "r", encoding="utf-8") as f:
        ingestor = create_ingestor(f)
        f.seek(0)
        for line in ingestor.stream_log():
            print(f"[{line.timestamp}] [{line.level.upper()}] {line.message} | meta: {line.metadata}")

    os.remove(log_path)

def test_metadata_injector_direct():
    raw_line = "##[group]Run pytest --verbose"
    log_line = LogLine(
        timestamp=None,
        level=None,
        message=raw_line,
        source="test_source",
        metadata={},
        raw_content=raw_line
    )
    injector = MetadataInjector.create_for_provider("github")
    enriched = injector.process(log_line)
    print(enriched)

def test_section_validation():
    lines = [
        LogLine(line_number=1, raw_content="section_start:1716816585:setup", timestamp="2023-06-15T14:23:41Z"),
        LogLine(line_number=2, raw_content="2023-06-15T14:23:42.456Z Running build step", timestamp="2023-06-15T14:23:42Z"),
    ]
    validator = SectionValidator()
    validated = validator.validate(lines)
    for log in validated:
        print(f"[{log.timestamp}] {log.raw_content}")

def test_tokenization_pipeline():
    log_path = "github_sample_log.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("2023-06-15T14:23:41.123Z Starting build\n")
        f.write("##[group]Build started\n")
        f.write("$ npm install\n")
        f.write("##[error] Missing dependency\n")
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

    for segment in segments:
        print(f"Segment {segment.segment_id} - Type: {segment.segment_type}, Lines: {segment.span}")
        print(f"Context: {segment.context}")
        print()

    os.remove(log_path)

def test_root_cause_analysis():
    log_path = "github_sample_log.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("2023-06-15T14:23:41.123Z Starting build\n")
        f.write("##[group]Build started\n")
        f.write("$ javac -xmx512 HelloWorld.java\n")
        f.write("##[error] javac: error: invalid flag: -xmx512\n")
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

    engine = RootCauseAnalysisEngine(classifiers=CLASSIFIERS)
    predictions = engine.analyze(segments)
    report = engine.generate_summary_report(predictions)

    print("Summary Report:")
    print(json.dumps(report, indent=2))

    os.remove(log_path)

if __name__ == "__main__":
    if MODE == "gitlab":
        test_gitlab_streaming()
    elif MODE == "multi":
        test_multi_source_streaming()
    elif MODE == "detect":
        test_auto_detection()
    elif MODE == "injector":
        test_metadata_injector_direct()
    elif MODE == "section_validate":
        test_section_validation()
    elif MODE == "tokenize":
        test_tokenization_pipeline()
    elif MODE == "analyze":
        test_root_cause_analysis()
