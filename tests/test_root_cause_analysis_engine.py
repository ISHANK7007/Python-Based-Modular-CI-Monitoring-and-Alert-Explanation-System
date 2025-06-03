from tokenization.classifiers.root_cause_engine import RootCauseAnalysisEngine
from tokenization.pipeline import TokenizationPipeline
from ingestion.github_actions import GitHubActionsIngestor
from tokenization.classifiers.rule_based_classifier import BuildFailureClassifier, OutOfMemoryClassifier

def run():
    print("=== Root Cause Engine Test ===")
    log_path = "logs/sample_log.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("##[group]Build step\n")
        f.write("javac Main.java\n")
        f.write("##[error] Compilation failed: error: cannot find symbol\n")
        f.write("##[endgroup]\n")

    ingestor = GitHubActionsIngestor(log_path)
    log_lines = ingestor.stream_log()

    pipeline = TokenizationPipeline(provider="github")
    tokenized_segments = pipeline.process(log_lines)

    engine = RootCauseAnalysisEngine(confidence_threshold=0.65, enable_telemetry=True)
    engine.register_classifier(BuildFailureClassifier("build_failure"))
    engine.register_classifier(OutOfMemoryClassifier("oom"))

    predictions = engine.analyze(tokenized_segments)
    telemetry_report = engine.get_telemetry_report()

    print("Predictions:")
    for p in predictions:
        print(p)

    if telemetry_report["regressions"]:
        print("Telemetry regressions detected:")
        for r in telemetry_report["regressions"]:
            for d in r["regressions"]:
                print(f"  - {d['type']} ({d['severity']}): {d['details']}")

if __name__ == "__main__":
    run()
