# tokenization/rules/github_rules.py

from tokenization.segment_rules import ClassificationRule

GITHUB_CLASSIFICATION_RULES = [
    ClassificationRule(classification_type="STACK_TRACE_LINE"),
    ClassificationRule(classification_type="STACK_TRACE_START"),
    ClassificationRule(classification_type="TEST_FAILURE"),
    ClassificationRule(classification_type="ASSERTION_ERROR"),
    ClassificationRule(classification_type="ERROR"),
    ClassificationRule(classification_type="WARNING"),
    ClassificationRule(classification_type="EXIT_CODE_NON_ZERO"),
]
