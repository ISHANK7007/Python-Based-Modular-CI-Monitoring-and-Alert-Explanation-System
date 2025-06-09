class BatchRetrainingStrategy:
    def apply(self, feedback_batch, classifier):
        # Add to accumulated feedback
        self.feedback_store.add_batch(feedback_batch)
        
        # Check if retraining criteria are met
        if not self._should_retrain(classifier):
            return
            
        # 1. Prepare training data with new feedback
        training_data = self.dataset_builder.build(
            base_dataset=classifier.get_training_data(),
            feedback=self.feedback_store.get_for_classifier(classifier.id),
            augmentation_ratio=self.config.feedback_amplification_factor
        )
        
        # 2. Train candidate model
        candidate_model = classifier.create_candidate(training_data)
        
        # 3. Evaluate & validate
        evaluation = self.model_evaluator.compare_models(
            classifier.current_model, 
            candidate_model,
            test_set=self.test_set_manager.get(classifier.id)
        )
        
        # 4. Deploy if improved
        if evaluation.is_improved() and not evaluation.has_regressions():
            classifier.deploy_candidate(candidate_model)
            self.metrics.record_deployment(classifier.id, evaluation)