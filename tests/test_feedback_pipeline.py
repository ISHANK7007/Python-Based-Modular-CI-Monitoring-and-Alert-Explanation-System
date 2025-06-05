import sys
import os
import unittest

# Add parent directory to sys.path for module resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.feedback_processor import FeedbackProcessor, Severity, ValidationResult

# Dummy components
class DummyValidator:
    def validate(self, feedback):
        return ValidationResult(valid=True, stage="validated")

class DummyAdjuster:
    def adjust(self, feedback, instructions):
        return feedback

class DummyChecker:
    def check(self, feedback):
        return ValidationResult(valid=True, stage="adjusted")

class DummyImpact:
    def analyze(self, feedback):
        return type("Impact", (), {
            "risk_score": 0.2,
            "details": {},
            "regression_detected": False
        })()

class DummyLogger:
    def log(self, x): print("[Warning]", x)


class TestFeedbackProcessing(unittest.TestCase):

    def setUp(self):
        self.processor = FeedbackProcessor(
            syntactic_validator=DummyValidator(),
            semantic_validator=DummyValidator(),
            feedback_adjuster=DummyAdjuster(),
            consistency_checker=DummyChecker(),
            impact_analyzer=DummyImpact(),
            config=type("Config", (), {"risk_threshold": 0.5})(),
            warning_logger=DummyLogger()
        )

    def test_TC1_valid_feedback(self):
        feedback_event = {
            "original_prediction": "OUT_OF_MEMORY",
            "corrected_label": "TEST_FAILURE",
            "reason": "Misclassified traceback",
            "job_id": "job_001",
            "segment_id": "s1"
        }
        result = self.processor.process_feedback(feedback_event)
        self.assertTrue(result.valid)
        self.assertEqual(result.stage, "adjusted")

    def test_TC2_confidence_high_feedback(self):
        class HighConfidenceChecker:
            def check(self, feedback):
                return ValidationResult(
                    valid=False,
                    stage="manual_review",
                    severity=Severity.HIGH,
                    details=["High confidence, manual review required"]
                )

        self.processor.consistency_checker = HighConfidenceChecker()

        feedback_event = {
            "original_prediction": "BUILD_FAILURE",
            "corrected_label": "TOOLCHAIN_ERROR",
            "job_id": "job_002",
            "segment_id": "s2"
        }

        result = self.processor.process_feedback(feedback_event)
        self.assertFalse(result.valid)
        self.assertEqual(result.stage, "manual_review")  # ✅ Assert the correct failure stage


if __name__ == "__main__":
    unittest.main()
