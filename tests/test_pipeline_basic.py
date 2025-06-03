import sys
import os
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tokenization.pipeline import TokenizationPipeline
from ingestion.github_actions import GitHubActionsIngestor
from tokenization.tokenizer import BasicTokenizer
from tokenization.segment_classifier import SimpleSegmentClassifier
from tokenization.context_classifier import ContextAwareClassifier
from tokenization.groupers.default_grouper import DefaultGrouper

# ANSI escape stripping fallback
ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

def strip_ansi(line: str) -> str:
    return ANSI_ESCAPE_PATTERN.sub("", line)

# Patch GitHubActionsIngestor to override _preprocess_ansi_codes
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
    print("=== Test: Basic Tokenization ===")

    log_path = "basic_log.txt"
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("2023-06-15T14:23:41.123Z [info] Starting build\n")
        f.write("##[group]Install dependencies\n")
        f.write("2023-06-15T14:23:42.456Z [warning] Using deprecated API\n")
        f.write("$ npm install\n")
        f.write("2023-06-15T14:23:45.789Z [error] npm ERR! code ELIFECYCLE\n")
        f.write("2023-06-15T14:23:46.000Z [error] npm ERR! Failed at the build script\n")
        f.write("2023-06-15T14:23:46.123Z [error] Exit status 1\n")
        f.write("##[endgroup]\n")
        f.write("##[error]Build failed file=main.py,line=42,endLine=42,col=5,endColumn=10\n")

    ingestor = PatchedGitHubActionsIngestor(log_path)
    log_lines = list(ingestor.stream_log(log_path))  # Force materialization for reuse

    print("\n=== Raw LogLines ===")
    for line in log_lines:
        # Try multiple known field options, fall back to string if needed
        try:
            print(f"- {line.value}")
        except AttributeError:
            try:
                print(f"- {line.line}")
            except AttributeError:
                print(f"- {line}")  # Final fallback

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
        print("No segments were created. Check token classifier and grouping logic.\n")
        return

    for segment in segments:
        print(f"Segment ID: {segment.segment_id}")
        print(f"Type: {segment.segment_type}")
        print(f"Span: {segment.span} lines")
        print(f"Context: {segment.context}")
        print("-" * 50)

if __name__ == "__main__":
    run()
