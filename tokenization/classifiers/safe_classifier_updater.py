# tokenization/classifiers/safe_classifier_updater.py

class UpdateResult:
    """Represents the result of applying a batch of feedback to a classifier."""
    def __init__(self, group, status, reason=None, metrics=None):
        self.group = group
        self.status = status
        self.reason = reason
        self.metrics = metrics


class SafeClassifierUpdater:
    """
    Safely applies batches of validated feedback to classifiers.
    Supports rollback on detected regressions.
    """

    def __init__(self, classifier_snapshot, feedback_grouper,
                 classifier_updater, performance_evaluator):
        self.classifier_snapshot = classifier_snapshot
        self.feedback_grouper = feedback_grouper
        self.classifier_updater = classifier_updater
        self.performance_evaluator = performance_evaluator

    def apply_feedback_batch(self, classifier, validated_feedback):
        """
        Applies grouped feedback to the classifier with impact validation.

        Args:
            classifier (object): The classifier instance to be updated.
            validated_feedback (list): A list of validated feedback events.

        Returns:
            list[UpdateResult]: Results of each group update attempt.
        """
        # 1. Create a snapshot for rollback
        snapshot = self.classifier_snapshot.create(classifier)

        # 2. Group feedback by related label/category
        update_groups = self.feedback_grouper.group_by_related_labels(validated_feedback)

        results = []
        for group in update_groups:
            # Apply group and evaluate
            self.classifier_updater.apply_group(classifier, group)
            impact = self.performance_evaluator.evaluate(classifier)

            # Rollback if regression is detected
            if impact.regression_detected:
                self.classifier_snapshot.restore(classifier, snapshot)
                results.append(UpdateResult(
                    group=group,
                    status="rolled_back",
                    reason=impact.regression_details
                ))
            else:
                results.append(UpdateResult(
                    group=group,
                    status="applied",
                    metrics=impact.metrics
                ))

        return results
