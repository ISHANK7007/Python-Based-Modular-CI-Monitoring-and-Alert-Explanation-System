from tokenization.metrics.analyze_log import RootCauseAnalysisEngine
from tokenization.classifiers.registry_setup import (
    BuildFailureClassifier,
    OutOfMemoryClassifier,
    MissingDependencyClassifier,
)
from tokenization.models import TokenizedSegment  # Or wherever segments are defined

# Example: Pretend tokenized segments (replace with real tokenizer output)
tokenized_segments = [
    TokenizedSegment(segment_id="segment_42", tokens=["Java heap space", "Memory: 512MB"]),
    # ... additional segments
]

# Create the analysis engine
engine = RootCauseAnalysisEngine(confidence_threshold=0.65)

# Register classifiers
engine.register_classifier(BuildFailureClassifier("build_failure"))
engine.register_classifier(OutOfMemoryClassifier("oom"))
engine.register_classifier(MissingDependencyClassifier("missing_dep"))

# Analyze segments
final_predictions = engine.analyze(tokenized_segments)

# Output results
for pred in final_predictions:
    print(pred)
