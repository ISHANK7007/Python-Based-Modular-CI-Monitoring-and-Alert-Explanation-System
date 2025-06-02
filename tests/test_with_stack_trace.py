from tokenization.pipeline import TokenizationPipeline
from ingestion.github_actions import GitHubActionsIngestor
from core.root_cause_prediction import RootCauseAnalysisEngine
from tokenization.tokenizer import BasicTokenizer
from tokenization.segment_classifier import SegmentClassifier
from tokenization.context_analyzer import ContextAnalyzer
from tokenization.grouping import GroupingStrategy
from tokenization.classifiers.rule_based_classifier import BuildFailureClassifier, OutOfMemoryClassifier

def test_with_stack_trace_log():
    log_path = "logs/test_with_stack_trace_log.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("Traceback (most recent call last):\n")
        f.write("  File \"main.py\", line 1, in <module>\n")
        f.write("ZeroDivisionError: division by zero\n")

    ingestor = GitHubActionsIngestor(log_path)
    log_lines = ingestor.stream_log(log_path)

    pipeline = TokenizationPipeline(
        tokenizer=BasicTokenizer(),
        segment_classifier=SegmentClassifier(classification_rules=[
            BuildFailureClassifier(name="build_failure", label="BUILD_FAILURE"),
            OutOfMemoryClassifier(name="oom", label="OOM")
        ]),
        context_analyzer=ContextAnalyzer(),
        grouping_strategy=GroupingStrategy()
    )
    segments = pipeline.process(log_lines)

    engine = RootCauseAnalysisEngine()
    for clf in pipeline.segment_classifier.classification_rules:
        engine.register_classifier(clf)

    predictions = engine.analyze(segments)
    assert len(predictions) >= 1
