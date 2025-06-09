import sys
import os
import unittest

# Ensure the main project directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ingestion.github_actions import GitHubActionsIngestor
from tokenization.pipeline import TokenizationPipeline
from tokenization.pattern_tokenizer import PatternBasedTokenizer
from tokenization.segment_classifier import SegmentClassifier
from tokenization.grouping import SectionBasedGrouping
from tokenization.context_analyzer import ContextAnalyzer
from tokenization.patterns.github_patterns import GITHUB_PATTERNS
from tokenization.rules.github_rules import GITHUB_CLASSIFICATION_RULES

def create_pipeline():
    tokenizer = PatternBasedTokenizer(GITHUB_PATTERNS)
    segment_classifier = SegmentClassifier(classification_rules=GITHUB_CLASSIFICATION_RULES)
    grouping_strategy = SectionBasedGrouping()
    context_analyzer = ContextAnalyzer()
    return TokenizationPipeline(
        tokenizer=tokenizer,
        segment_classifier=segment_classifier,
        context_analyzer=context_analyzer,
        grouping_strategy=grouping_strategy
    )

class TestTokenizationPipeline(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = os.path.abspath("tests/temp_logs")
        os.makedirs(self.tmp_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.tmp_dir):
            for file in os.listdir(self.tmp_dir):
                os.remove(os.path.join(self.tmp_dir, file))
            os.rmdir(self.tmp_dir)

    def test_overlapping_token_conflict(self):
        """Should resolve conflict between TEST_FAILURE and ERROR using context."""
        log_file = os.path.join(self.tmp_dir, "test_log_1.txt")
        with open(log_file, "w") as f:
            f.write("FAIL: test_example\nAssertionError: expected 1 but got 0\n")

        ingestor = GitHubActionsIngestor()
        log_lines = ingestor.stream_log(source=log_file)
        pipeline = create_pipeline()
        segments = list(pipeline.process(log_lines))

        self.assertEqual(len(segments), 1)
        self.assertIn(segments[0].segment_type, ["TEST_FAILURE", "ERROR"])
        self.assertIn(segments[0].context.get("classification"), ["TEST_FAILURE", "ERROR"])

    def test_traceback_buffering(self):
        """Should identify stack traces using buffered context."""
        log_file = os.path.join(self.tmp_dir, "test_log_2.txt")
        with open(log_file, "w") as f:
            f.write(
                "Traceback (most recent call last):\n"
                "  File \"main.py\", line 1, in <module>\n"
                "    1 / 0\n"
                "ZeroDivisionError: division by zero\n"
            )

        ingestor = GitHubActionsIngestor()
        log_lines = ingestor.stream_log(source=log_file)
        pipeline = create_pipeline()
        segments = list(pipeline.process(log_lines))

        self.assertTrue(any("STACK_TRACE" in s.segment_type for s in segments))
        self.assertTrue(any(s.context.get("classification") == "stack_trace" for s in segments))

    def test_false_positive_and_scoping(self):
        """Should suppress false positives and detect scoped segments."""
        log_file = os.path.join(self.tmp_dir, "test_log_3.txt")
        with open(log_file, "w") as f:
            f.write(
                "error tolerance set to 0.2\n"
                "Tests failed: 2 failures\n"
                "Job failed (code: 1)\n"
            )

        ingestor = GitHubActionsIngestor()
        log_lines = ingestor.stream_log(source=log_file)
        pipeline = create_pipeline()
        segments = list(pipeline.process(log_lines))

        self.assertFalse(any("error tolerance" in s.raw_text.lower() and s.segment_type == "ERROR" for s in segments))
        self.assertTrue(any("Tests failed" in s.raw_text and s.segment_type == "TEST_FAILURE" for s in segments))
        self.assertTrue(any("Job failed" in s.raw_text and s.segment_type == "EXIT_CODE_NON_ZERO" for s in segments))

if __name__ == "__main__":
    unittest.main()
