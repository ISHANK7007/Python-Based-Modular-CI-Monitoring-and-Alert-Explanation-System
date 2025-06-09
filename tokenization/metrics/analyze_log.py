from tokenization.classifiers.rule_based_classifier import BuildFailureClassifier, OutOfMemoryClassifier
from tokenization.classifiers.root_cause_engine import RootCauseAnalysisEngine
from tokenization.pipeline import tokenizer

# Analysis process with fallback
def analyze_ci_log(log_segments):
    # 1. Tokenize and score segments
    tokenized_segments = tokenizer.tokenize(log_segments)
    
    # 2. Initialize analysis engine with fallback
    engine = RootCauseAnalysisEngine(
        confidence_threshold=0.65,
        enable_fallback=True,
        fallback_confidence_ceiling=0.6
    )
    
    # 3. Register regular classifiers
    engine.register_classifier(BuildFailureClassifier("build_failure"))
    engine.register_classifier(OutOfMemoryClassifier("oom"))
    # ... register other classifiers
    
    # 4. Analyze with fallback support
    predictions = engine.analyze(tokenized_segments)
    
    # 5. Always returns predictions, even if just fallback classifications
    return predictions
