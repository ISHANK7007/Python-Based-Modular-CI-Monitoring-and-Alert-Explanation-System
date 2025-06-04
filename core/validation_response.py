# core/validation_response.py

from enum import Enum


class ValidationResponse(Enum):
    """Standard responses produced by the feedback validation system."""

    REJECT = "reject"                        # Refuse the feedback entirely
    FLAG_FOR_REVIEW = "flag_for_review"      # Queue feedback for human review
    AUTO_ADJUST = "auto_adjust"              # Automatically adjust to valid state
    ACCEPT_WITH_WARNING = "accept_with_warning"  # Log concerns but apply feedback anyway
