from core.feedback_processor import retrain_classifier
from tokenization.pipeline import run_classification
from tests.classification.mock_utils import (
    setup_isolated_feedback_db,
    apply_feedback,
    has_expected_misclassifications,
    corrections_applied,
    classification_metrics_improved
)

TEST_LOG_PATH = "tests/fixtures/test_log_sample.txt"
FEEDBACK_CORRECTIONS_PATH = "tests/fixtures/feedback_corrections.json"

def test_classifier_improves_with_feedback():
    # 1. Set up a clean test environment with isolated feedback DB
    temp_feedback_db = setup_isolated_feedback_db()

    # 2. Run initial classification
    initial_results = run_classification(TEST_LOG_PATH, feedback_db=temp_feedback_db)

    # 3. Verify initial classification contains expected misclassifications
    assert has_expected_misclassifications(initial_results), \
        "Initial classification did not produce expected errors."

    # 4. Apply synthetic feedback to correct known misclassifications
    apply_feedback(FEEDBACK_CORRECTIONS_PATH, feedback_db=temp_feedback_db)

    # 5. Trigger classifier retraining based on applied feedback
    retrain_classifier(feedback_db=temp_feedback_db)

    # 6. Run classification again on the same input
    improved_results = run_classification(TEST_LOG_PATH, feedback_db=temp_feedback_db)

    # 7. Verify feedback corrections were applied in the second pass
    assert corrections_applied(improved_results, FEEDBACK_CORRECTIONS_PATH), \
        "Corrections from feedback were not reflected in improved results."

    # 8. Verify classification metrics have improved
    assert classification_metrics_improved(initial_results, improved_results), \
        "Metrics did not improve after retraining with feedback."
