from tokenization.classifiers.root_cause_engine import RootCauseAnalysisEngine

from tokenization.pipeline import TokenizationPipeline
from ingestion.github_actions import GitHubActionsIngestor
from tokenization.classifiers.rule_based_classifier import BuildFailureClassifier, OutOfMemoryClassifier

# Simulate or stream a real log
ingestor = GitHubActionsIngestor("path/to/log.txt")
log_lines = ingestor.stream_log()

# Tokenize segments
pipeline = TokenizationPipeline(provider="github")
tokenized_segments = pipeline.process(log_lines)

# Run root cause analysis with telemetry
engine = RootCauseAnalysisEngine(confidence_threshold=0.65, enable_telemetry=True)
engine.register_classifier(BuildFailureClassifier("build_failure"))
engine.register_classifier(OutOfMemoryClassifier("oom"))

predictions = engine.analyze(tokenized_segments)
telemetry_report = engine.get_telemetry_report()

# Print telemetry report
if telemetry_report.get("regressions"):
    for reg in telemetry_report["regressions"]:
        for r in reg["regressions"]:
            print(f"Regression: {r['type']} ({r['severity']}): {r['details']}")
