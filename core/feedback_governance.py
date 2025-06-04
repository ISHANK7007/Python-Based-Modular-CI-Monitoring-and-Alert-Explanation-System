# core/feedback_governance.py

from enum import Enum


class ReviewLevel(Enum):
    """Defines escalation levels for flagged feedback review."""
    STANDARD = "standard"
    ELEVATED = "elevated"
    CRITICAL = "critical"


class FeedbackGovernance:
    """Routes flagged feedback to appropriate reviewers based on severity and impact."""

    def __init__(self, review_queue, alerts):
        self.review_queue = review_queue
        self.alerts = alerts

    def process_flagged_feedback(self, feedback, validation_results):
        """Dispatch feedback for review based on validation severity and review level."""
        review_level = self._determine_review_level(validation_results)

        if review_level == ReviewLevel.STANDARD:
            self.review_queue.add(feedback, reviewer_role="classifier_maintainer")
        elif review_level == ReviewLevel.ELEVATED:
            self.review_queue.add(feedback, reviewer_role="domain_expert")
            self.alerts.notify_domain_expert(feedback, validation_results)
        elif review_level == ReviewLevel.CRITICAL:
            self.review_queue.add(feedback, reviewer_role="system_architect")
            self.alerts.escalate_to_architect(feedback, validation_results)

    def _determine_review_level(self, validation_results):
        """
        Logic to determine review level from validation results.
        (This is a stub; replace with actual heuristics.)
        """
        return validation_results.get("review_level", ReviewLevel.STANDARD)
