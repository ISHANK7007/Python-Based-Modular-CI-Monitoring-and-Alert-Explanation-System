from tokenization.classifiers.multi_label_engine import EnhancedRootCauseAnalysisEngine
from tokenization.classifiers.registry_setup import BuildFailureClassifier, OutOfMemoryMultiLabelClassifier
from tokenization.models import TokenizedSegment

# Mocked tokenized segments (replace with actual tokenizer output in production)
tokenized_segments = [
    TokenizedSegment(segment_id="s1", tokens=["Out of memory", "Killed process"]),
    TokenizedSegment(segment_id="s2", tokens=["compilation failed", "exit code: 1"]),
]

# Create multi-label analysis engine
engine = EnhancedRootCauseAnalysisEngine(enable_multi_label=True)

# Register classifiers
engine.register_classifier(OutOfMemoryMultiLabelClassifier("oom_classifier"))
engine.register_classifier(BuildFailureClassifier("build_failure"))  # Regular classifier

# Get detailed multi-label analysis
prediction_bundles = engine.analyze_multi_label(tokenized_segments)

# Or get backwards-compatible single-label predictions
legacy_predictions = engine.analyze(tokenized_segments)

# Example output of a prediction bundle
if prediction_bundles:
    bundle = prediction_bundles[0]
    print(f"Primary cause: {bundle.primary_cause.label} ({bundle.primary_cause.confidence:.2f})")
    for cause in bundle.secondary_causes:
        print(f"  Secondary cause: {cause.label} ({cause.confidence:.2f})")
        print(f"    Evidence: {', '.join(cause.supporting_tokens[:2])}")
    for symptom in bundle.symptoms:
        print(f"  Symptom: {symptom.label} ({symptom.confidence:.2f})")
else:
    print("No prediction bundles returned.")
