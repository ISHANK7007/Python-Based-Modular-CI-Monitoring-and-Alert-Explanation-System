from tokenization.classifiers.registry_setup import EnhancedClassifierRegistry
from tokenization.classifiers.registry_setup import BuildFailureClassifier, OutOfMemoryClassifier
from tokenization.models import TokenizedSegment

# Mock tokenized segments for demonstration
tokenized_segments = [
    TokenizedSegment(segment_id="segment_42", tokens=["compilation failed", "exit code: 1"]),
    TokenizedSegment(segment_id="segment_43", tokens=["build started"])
]

# Create classifier registry
registry = EnhancedClassifierRegistry()

# Register classifiers with metadata-aware rules
registry.register(BuildFailureClassifier("build_failure"))
registry.register(OutOfMemoryClassifier("oom"))

# Apply to tokenized segments
predictions = registry.classify(tokenized_segments)

# Print prediction results
for pred in predictions:
    print(pred)
