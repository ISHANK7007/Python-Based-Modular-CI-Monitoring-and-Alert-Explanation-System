# tokenization/classifiers/feedback_adaptation_manager.py

from tokenization.classifiers.strategies.incremental_rule_strategy import IncrementalRuleStrategy
from tokenization.classifiers.strategies.batch_retraining_strategy import BatchRetrainingStrategy

# Placeholder strategy classes assumed to exist elsewhere
class HierarchicalAdaptationStrategy:
    def __init__(self, strategy_tiers):
        self.strategy_tiers = strategy_tiers

    def apply(self, feedback_batch, classifier):
        for strategy, portion in self.strategy_tiers:
            # Portion-based delegation (simplified stub)
            subset = feedback_batch[:int(len(feedback_batch) * portion)]
            strategy.apply(subset, classifier)

class NoopStrategy:
    def apply(self, feedback_batch, classifier):
        pass


class FeedbackAdaptationManager:
    """
    Selects and applies the appropriate feedback adaptation strategy
    based on the classifier type.
    """

    def __init__(self, config):
        self.config = config

    def apply_feedback(self, feedback_batch, classifiers):
        """
        Applies feedback to each classifier using an appropriate strategy.

        Args:
            feedback_batch (list): Validated feedback events.
            classifiers (list): List of classifiers to update.
        """
        for classifier in classifiers:
            strategy = self._select_strategy(classifier, feedback_batch)
            strategy.apply(feedback_batch, classifier)

    def _select_strategy(self, classifier, feedback_batch):
        """
        Determines which adaptation strategy to use for the given classifier.

        Returns:
            Strategy instance
        """
        if isinstance(classifier, RuleBasedClassifier):
            return IncrementalRuleStrategy(safety_level=self.config.safety_level)
        elif isinstance(classifier, MLBasedClassifier):
            return BatchRetrainingStrategy(
                min_samples=self.config.min_samples_for_retraining,
                training_fraction=0.8
            )
        elif isinstance(classifier, HybridClassifier):
            return HierarchicalAdaptationStrategy([
                (IncrementalRuleStrategy(), self.config.rule_feedback_portion),
                (BatchRetrainingStrategy(), self.config.ml_feedback_portion)
            ])
        else:
            return NoopStrategy()  # Fallback for unknown or special classifiers


# Example classifier stubs for strategy dispatch resolution
class RuleBasedClassifier: pass
class MLBasedClassifier: pass
class HybridClassifier: pass
