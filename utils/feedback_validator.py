# utils/feedback_validator.py

class ValidationError(Exception):
    """Custom exception for feedback validation errors."""
    pass


class ValidationResult:
    """Simple result wrapper to return validation outcomes."""
    def __init__(self, valid=True, conflict_type=None, similar_segments=None):
        self.valid = valid
        self.conflict_type = conflict_type
        self.similar_segments = similar_segments


class FeedbackValidator:
    def __init__(self, taxonomy, segment_registry, compatibility_matrix, segment_finder, feedback_store):
        self.taxonomy = taxonomy
        self.segment_registry = segment_registry
        self.compatibility_matrix = compatibility_matrix
        self.segment_finder = segment_finder
        self.feedback_store = feedback_store

    def validate_feedback(self, feedback_event):
        """Performs schema-level validation on required fields."""
        required_fields = ['original_prediction', 'corrected_label', 'job_id', 'segment_id']
        for field in required_fields:
            if field not in feedback_event:
                raise ValidationError(f"Missing required field: {field}")

        # Additional type and value validations could be added here

    def validate_label_domain(self, feedback):
        """Ensures correction stays within the permitted label domain."""
        if feedback.original_prediction.category != feedback.corrected_label.category:
            if not self.taxonomy.is_cross_category_allowed(
                feedback.original_prediction.category,
                feedback.corrected_label.category
            ):
                raise ValidationError(
                    f"Cross-category correction from {feedback.original_prediction.category} "
                    f"to {feedback.corrected_label.category} is not permitted"
                )

    def validate_segment_scope(self, feedback):
        """Checks if the corrected label is valid for the segment type."""
        segment_type = self.segment_registry.get_type(feedback.segment_id)
        if not self.compatibility_matrix.is_valid(segment_type, feedback.corrected_label):
            raise ValidationError(
                f"Label {feedback.corrected_label} cannot be applied to segment type {segment_type}"
            )

    def check_pattern_consistency(self, feedback):
        """Detects conflicts with past feedback on similar segments."""
        similar_segments = self.segment_finder.find_similar(
            segment_id=feedback.segment_id,
            similarity_threshold=0.85
        )

        corrections_on_similar = self.feedback_store.get_for_segments(similar_segments)
        if self._has_contradicting_corrections(corrections_on_similar, feedback):
            return ValidationResult(
                valid=False,
                conflict_type="pattern_inconsistency",
                similar_segments=similar_segments
            )
        return ValidationResult(valid=True)

    def _has_contradicting_corrections(self, corrections, new_feedback):
        # Placeholder logic to detect contradictions (to be implemented as needed)
        return False
