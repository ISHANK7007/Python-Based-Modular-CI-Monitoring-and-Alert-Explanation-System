from tokenization.classifiers.root_cause_engine import RootCauseAnalysisEngine
from tokenization.classifiers.rule_based_classifier import BuildFailureClassifier, OutOfMemoryClassifier
from tokenization.pipeline import TokenizationPipeline

# Simulate raw CI log lines (replace with actual file reading if needed)
log_lines = [
    "##[group]Build step",
    "javac: error: invalid flag: -xmx512",
    "exit code: 1",
    "##[endgroup]"
]

# Tokenize the log
pipeline = TokenizationPipeline(provider="github")
tokenized_segments = pipeline.process(log_lines)

# Analyze CI logs
engine = RootCauseAnalysisEngine(confidence_threshold=0.7)
engine.register_classifier(BuildFailureClassifier("build_failure"))
engine.register_classifier(OutOfMemoryClassifier("oom"))

# Get predictions with detailed segment references
predictions = engine.analyze(tokenized_segments)

# Generate a summary report with traceability
report = engine.generate_summary_report(predictions)

# Print structured report
import json
print(json.dumps(report, indent=2))
