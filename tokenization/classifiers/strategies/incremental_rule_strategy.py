class IncrementalRuleStrategy:
    def apply(self, feedback_batch, classifier):
        # Group feedback by affected pattern/rule
        grouped_feedback = self._group_by_pattern(feedback_batch)
        
        for pattern_id, feedback_items in grouped_feedback.items():
            # 1. Check consistency within the group
            if not self._is_consistent(feedback_items):
                self.review_queue.add(feedback_items, "inconsistent_pattern_feedback")
                continue
                
            # 2. Generate rule adjustment candidates
            rule_candidates = self.rule_generator.generate_candidates(
                pattern_id, 
                feedback_items,
                classifier.get_current_rule(pattern_id)
            )
            
            # 3. Evaluate candidates on historical data
            best_candidate = self._evaluate_candidates(rule_candidates)
            
            # 4. Apply with safeguards
            if best_candidate.score > self.config.min_improvement_threshold:
                self._apply_rule_with_monitoring(
                    classifier, 
                    pattern_id, 
                    best_candidate.rule,
                    feedback_items
                )