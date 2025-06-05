import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tokenization.pipeline import TokenizationPipeline
from tokenization.tokenizer import BasicTokenizer
from tokenization.segment_classifier import SimpleSegmentClassifier
from tokenization.context_classifier import ContextAwareClassifier
from tokenization.groupers.default_grouper import DefaultGrouper

# ANSI escape stripping pattern
ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(line: str) -> str:
    return ANSI_ESCAPE_PATTERN.sub("", line)

# Patched GitHubActionsIngestor with ANSI stripping and context tracking
from ingestion.github_actions import GitHubActionsIngestor as OriginalGitHubIngestor

class PatchedGitHubActionsIngestor(OriginalGitHubIngestor):
    def _get_preprocessors(self):
        return [
            self._patched_preprocess_ansi_codes,
            self._track_step_context
        ]

    def _patched_preprocess_ansi_codes(self, lines):
        for line_number, line in lines:
            cleaned = strip_ansi(line)
            yield (line_number, cleaned)

def run():
    print("=== Test: Section With Error ===")

    log_path = "error_log.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("##[group]Run tests\n")
        f.write("pytest tests/\n")
        f.write("##[error] AssertionError: expected True but got False\n")
        f.write("##[endgroup]\n")

    ingestor = PatchedGitHubActionsIngestor(log_path)
    log_lines = list(ingestor.stream_log(log_path))  # Materialize generator

    print("\n=== Raw LogLines ===")
    for line in log_lines:
        try:
            print(f"- {line.value}")
        except AttributeError:
            print(f"- {line}")

    tokenizer = BasicTokenizer()
    segment_classifier = SimpleSegmentClassifier()
    context_analyzer = ContextAwareClassifier()
    grouping_strategy = DefaultGrouper()

    pipeline = TokenizationPipeline(
        tokenizer=tokenizer,
        segment_classifier=segment_classifier,
        context_analyzer=context_analyzer,
        grouping_strategy=grouping_strategy
    )

    segments = pipeline.process(log_lines)

    print("\n=== Tokenized Segments ===")
    if not segments:
        print("No segments were created. Check error parsing and grouping logic.\n")
        return

    for segment in segments:
        print(f"Segment ID: {segment.segment_id}")
        print(f"Type: {segment.segment_type}")
        print(f"Span: {segment.span} lines")
        print(f"Context: {segment.context}")
        print(f"Contains Error: {segment.contains_error}")
        print("-" * 50)

if __name__ == "__main__":
    run()
