from tokenization.classifiers.registry_core import (
    RootCauseClassifierRegistry,
    BuildFailureClassifier,
    OutOfMemoryClassifier,
    MissingDependencyClassifier
)
from tokenization.models import TokenizedSegment

# Mock segments for classification
tokenized_segments = [
    TokenizedSegment(
        segment_id="s1",
        tokens=["compilation failed", "exit code: 1"],
        segment_type="UNKNOWN",
        confidence=0.0,
        context={"job_id": "build-java", "section": "maven-compile", "line_range": [1024, 1025]}
    ),
    TokenizedSegment(
        segment_id="s2",
        tokens=["Out of memory", "Java heap space"],
        segment_type="UNKNOWN",
        confidence=0.0,
        context={"job_id": "test-java", "section": "test-runtime", "line_range": [204, 208]}
    )
]

# Create classifier registry
registry = RootCauseClassifierRegistry()

# Register classifiers
registry.register(BuildFailureClassifier("build_failure", "BUILD_FAILURE"))
registry.register(OutOfMemoryClassifier("oom", "OUT_OF_MEMORY"))
registry.register(MissingDependencyClassifier("missing_dep", "MISSING_DEPENDENCY"))

# Classify segments
predictions = registry.classify(tokenized_segments)

# Output predictions
for pred in predictions:
    print(pred)
