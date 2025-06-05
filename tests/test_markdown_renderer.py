import unittest
import sys
import os

# Ensure root directory is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tokenization.classifiers.markdown_renderer import GitHubMarkdownRenderer
from core.root_cause_prediction import RootCausePrediction
from tokenization.token_relationship import TokenizedSegment


class TestGitHubMarkdownRenderer(unittest.TestCase):
    def setUp(self):
        self.renderer = GitHubMarkdownRenderer()

    def test_render_test_failure_segment(self):
        """✅ TC1: Render Markdown for test failure segment with summary and log excerpt."""
        segment = TokenizedSegment(
            segment_id="segment_001",
            tokens=["Test failed", "AssertionError: expected 200 but got 500"],
            segment_type="TEST_FAILURE",
            confidence=0.91,
            context={"job_id": "job_001", "section": "unit_tests"}
        )
        segment.metadata = {
            "summary": "AssertionError: expected 200 but got 500",
            "excerpt": "Traceback (most recent call...)\nAssertionError: expected 200 but got 500",
            "span": "21–25"
        }

        prediction = RootCausePrediction(
            label="TEST_FAILURE",
            confidence=0.91,
            segment_ids=["segment_001"],
            metadata=segment.metadata
        )

        markdown = self.renderer.render([prediction])
        print("\n=== TC1 Markdown Output ===\n", markdown)

        self.assertIn("TEST_FAILURE", markdown)
        self.assertIn("AssertionError", markdown)
        self.assertIn("Traceback", markdown)

    def test_render_fallback_for_low_confidence(self):
        """✅ TC2: Render fallback explanation for unclassified or low-confidence prediction."""
        prediction = RootCausePrediction(
            label="UNCLASSIFIED",
            confidence=0.35,
            segment_ids=[],
            metadata={"info": "Low confidence fallback test"}
        )

        markdown = self.renderer.render([prediction])
        print("\n=== TC2 Markdown Output ===\n", markdown)

        self.assertIn("UNCLASSIFIED", markdown)
        self.assertIn("Low confidence", markdown)


if __name__ == '__main__':
    unittest.main()
