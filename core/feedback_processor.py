# core/feedback_processor.py

class ValidationResult:
    """Result of a validation step."""
    def __init__(self, valid, stage=None, details=None, severity=None):
        self.valid = valid
        self.stage = stage
        self.details = details
        self.severity = severity  # ✅ Added to support severity-based decisions
        self.warnings = []


class Severity:
    """Stub enum for severity levels."""
    HIGH = "high"
    LOW = "low"


class FeedbackProcessor:
    """Processes feedback through multiple validation and adjustment stages."""

    def __init__(self, syntactic_validator, semantic_validator, feedback_adjuster,
                 consistency_checker, impact_analyzer, config, warning_logger):
        self.syntactic_validator = syntactic_validator
        self.semantic_validator = semantic_validator
        self.feedback_adjuster = feedback_adjuster
        self.consistency_checker = consistency_checker
        self.impact_analyzer = impact_analyzer
        self.config = config
        self.warning_logger = warning_logger

    def process_feedback(self, feedback_event):
        """Validates, adjusts, and evaluates incoming feedback before ingestion."""

        # 1. Basic validation
        syntactic_result = self.syntactic_validator.validate(feedback_event)
        if not syntactic_result or not getattr(syntactic_result, "valid", False):
            return ValidationResult(valid=False, stage="syntactic")

        # 2. Semantic validation
        semantic_result = self.semantic_validator.validate(feedback_event)
        if not semantic_result.valid:
            if getattr(semantic_result, "can_auto_adjust", False):
                feedback_event = self.feedback_adjuster.adjust(
                    feedback_event,
                    getattr(semantic_result, "adjustment_instructions", None)
                )
            else:
                return ValidationResult(
                    valid=False,
                    stage="semantic",
                    details=getattr(semantic_result, "details", None)
                )

        # 3. Consistency checking
        consistency_result = self.consistency_checker.check(feedback_event)
        if not consistency_result.valid:
            if consistency_result.severity == Severity.HIGH:
                return ValidationResult(
                    valid=False,
                    stage=getattr(consistency_result, "stage", "consistency_check"),
                    details=consistency_result.warnings,
                    severity=Severity.HIGH  # ✅ Properly carry forward severity
                )
            else:
                self.warning_logger.log(consistency_result)
                feedback_event.metadata = getattr(feedback_event, "metadata", {})
                feedback_event.metadata["warnings"] = consistency_result.warnings

        # 4. Impact analysis
        if self._is_high_risk(feedback_event):
            impact = self.impact_analyzer.analyze(feedback_event)
            if impact.risk_score > self.config.risk_threshold:
                return ValidationResult(
                    valid=False,
                    stage="impact_analysis",
                    details=impact.details
                )

        # ✅ Final success case
        return ValidationResult(valid=True, stage="adjusted")

    def _is_high_risk(self, feedback_event):
        """Stub risk evaluation (can be replaced with heuristics or rules)."""
        return getattr(feedback_event, "risk_level", "low") == "high"
