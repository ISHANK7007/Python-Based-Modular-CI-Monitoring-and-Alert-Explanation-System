import sys
import os
import unittest

# Add Output_code/ to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))
sys.path.insert(0, project_root)

from cli.live_row_formatter import format_row
from cli.interactive_commands import InteractiveCommandHandler

class DummySegment:
    def __init__(self, job_id, step, label, confidence, raw_text, status="FAIL"):
        self.job_id = job_id
        self.step = step
        self.segment_type = label
        self.confidence = confidence
        self.raw_text = raw_text
        self.segment_id = f"{job_id}_{step}"
        self.status = status

class TestCLIStreaming(unittest.TestCase):

    def test_render_multiple_test_failures(self):
        print("\n🧪 TC1: Rendering 20 TEST_FAILURE logs")
        segments = [
            DummySegment(f"job_{i}", "test", "TEST_FAILURE", 0.72, f"Error line {i}")
            for i in range(20)
        ]
        rendered = [format_row({
            "job_id": s.job_id,
            "step": s.step,
            "label": s.segment_type,
            "confidence": s.confidence,
            "explanation_summary": s.raw_text,
            "status": s.status
        }) for s in segments]

        for row in rendered:
            print(row)
            self.assertIn("TEST_FAILURE", row)
            self.assertIn("confidence:", row)
        self.assertEqual(len(rendered), 20)

    def test_feedback_key_press(self):
        print("\n🧪 TC2: Simulating 'f' key press for feedback")
        handler = InteractiveCommandHandler()
        captured = []

        def mock_feedback():
            captured.append("feedback_triggered")
            print("[Mock CLI] Feedback submitted successfully for selected row.")

        handler.command_map["f"] = mock_feedback
        handler.handle("f")

        self.assertIn("feedback_triggered", captured)

if __name__ == '__main__':
    unittest.main()
