tests/feedback/
├── test_feedback_integration.py    # End-to-end feedback tests
├── test_feedback_persistence.py    # Storage and retrieval tests
├── test_retraining.py              # Classifier update tests
└── fixtures/
    ├── feedback_samples/           # Sample feedback JSON files
    │   ├── single_correction.json
    │   ├── multiple_corrections.json
    │   └── conflicting_feedback.json
    ├── pre_feedback_classifications/  # Expected results before feedback
    └── post_feedback_classifications/ # Expected results after feedback