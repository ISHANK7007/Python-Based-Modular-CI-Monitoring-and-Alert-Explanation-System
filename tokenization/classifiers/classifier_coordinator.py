from typing import List, Dict, Any, Optional, Callable, Tuple, Set
from dataclasses import dataclass
import logging
from collections import defaultdict

from core.root_cause_prediction import RootCausePrediction
from tokenization.models import TokenizedSegment
from tokenization.classifiers.rule_based_classifier import EnhancedRuleBasedClassifier
from tokenization.classifiers.registry_setup import EnhancedClassifierRegistry


class ClassifierCoordinator:
    """
    Coordinates multiple classifiers and resolves conflicts between competing predictions.
    
    Implements weighted scoring heuristics to determine the most likely root cause
    when multiple classifiers produce conflicting predictions for the same segments.
    """
    
    def __init__(self, 
                 base_confidence_threshold: float = 0.6,
                 conflict_resolution_strategy: str = "weighted_score",
                 label_priority_map: Optional[Dict[str, float]] = None,
                 segment_overlap_threshold: float = 0.5):
        """
        Initialize coordinator with conflict resolution parameters.
        
        Args:
            base_confidence_threshold: Minimum confidence to consider a prediction valid
            conflict_resolution_strategy: Strategy for resolving conflicts ('weighted_score', 
                                         'highest_confidence', 'priority_label')
            label_priority_map: Priority weights for different root cause labels
            segment_overlap_threshold: Percentage of shared segments to consider predictions in conflict
        """
        self.base_confidence_threshold = base_confidence_threshold
        self.conflict_resolution_strategy = conflict_resolution_strategy
        self.logger = logging.getLogger(__name__)
        
        # Define default label priorities if not provided
        self.label_priority_map = label_priority_map or {
            # Higher number = higher priority
            "SECURITY_VIOLATION": 5.0,   # Security issues highest priority
            "OUT_OF_MEMORY": 4.0,        # OOM issues next highest
            "PERMISSION_DENIED": 3.5,    # Permission issues high priority
            "TEST_FAILURE": 3.0,         # Test failures medium-high priority
            "BUILD_FAILURE": 2.5,        # Build failures medium priority
            "MISSING_DEPENDENCY": 2.0,   # Dependency issues medium-low priority
            "TIMEOUT": 1.5,              # Timeouts low-medium priority
            "CONFIGURATION_ERROR": 1.2,  # Config issues low priority
            "UNKNOWN": 1.0               # Unknown issues lowest priority
        }
        
        self.segment_overlap_threshold = segment_overlap_threshold
        
        # Define scoring functions for different strategies
        self.scoring_functions = {
            "weighted_score": self._calculate_weighted_score,
            "highest_confidence": lambda p: p.confidence,
            "priority_label": lambda p: self.label_priority_map.get(p.label, 0.0)
        }
        
    def coordinate(self, predictions: List[RootCausePrediction]) -> List[RootCausePrediction]:
        """
        Coordinate multiple predictions and resolve conflicts.
        
        Args:
            predictions: List of RootCausePrediction objects from various classifiers
            
        Returns:
            Filtered and ranked list of predictions with conflicts resolved
        """
        if not predictions:
            return []
            
        # Filter predictions below confidence threshold
        filtered_predictions = [p for p in predictions if p.confidence >= self.base_confidence_threshold]
        
        # If no predictions meet threshold, return empty list
        if not filtered_predictions:
            return []
            
        # Group predictions by segment overlap
        prediction_groups = self._group_overlapping_predictions(filtered_predictions)
        
        # Resolve conflicts within each group and collect results
        resolved_predictions = []
        for group in prediction_groups:
            if len(group) == 1:
                # No conflict if only one prediction in group
                resolved_predictions.append(group[0])
            else:
                # Resolve conflicts for multiple predictions covering same segments
                winner = self._resolve_conflict(group)
                resolved_predictions.append(winner)
                
        # Sort final predictions by confidence score
        resolved_predictions.sort(key=lambda p: p.confidence, reverse=True)
        
        return resolved_predictions
        
    def _group_overlapping_predictions(self, predictions: List[RootCausePrediction]) -> List[List[RootCausePrediction]]:
        """
        Group predictions that share significant segment overlap.
        
        Args:
            predictions: List of predictions to group
            
        Returns:
            List of prediction groups, where each group contains potentially conflicting predictions
        """
        # Initialize groups
        groups = []
        ungrouped = set(range(len(predictions)))
        
        while ungrouped:
            # Start a new group with the first ungrouped prediction
            current_index = min(ungrouped)
            current_group = [predictions[current_index]]
            current_segments = set(predictions[current_index].segment_ids)
            ungrouped.remove(current_index)
            
            # Find all predictions that overlap with this one
            to_check = list(ungrouped)
            for idx in to_check:
                pred = predictions[idx]
                pred_segments = set(pred.segment_ids)
                
                # Calculate overlap ratio
                if not pred_segments or not current_segments:
                    continue
                
                # Calculate Jaccard similarity for segment overlap
                intersection = current_segments.intersection(pred_segments)
                union = current_segments.union(pred_segments)
                overlap_ratio = len(intersection) / len(union)
                
                if overlap_ratio >= self.segment_overlap_threshold:
                    # Add to current group if significant overlap
                    current_group.append(pred)
                    current_segments.update(pred_segments)
                    ungrouped.remove(idx)
            
            groups.append(current_group)
            
        return groups
        
    def _resolve_conflict(self, predictions: List[RootCausePrediction]) -> RootCausePrediction:
        """
        Resolve conflicts between predictions using the selected strategy.
        
        Args:
            predictions: List of conflicting predictions
            
        Returns:
            The winning prediction according to the resolution strategy
        """
        if not predictions:
            raise ValueError("Cannot resolve conflict with empty predictions list")
            
        if len(predictions) == 1:
            return predictions[0]
            
        # Get scoring function based on strategy
        score_fn = self.scoring_functions.get(
            self.conflict_resolution_strategy, 
            self.scoring_functions["weighted_score"]
        )
        
        # Score each prediction
        scored_predictions = [(pred, score_fn(pred)) for pred in predictions]
        
        # Select prediction with highest score
        winner = max(scored_predictions, key=lambda p: p[1])[0]
        
        # Log conflict resolution details
        self._log_conflict_resolution(predictions, winner)
        
        return winner
    
    def _calculate_weighted_score(self, prediction: RootCausePrediction) -> float:
        """
        Calculate weighted score combining confidence and label priority.
        
        Args:
            prediction: Prediction to score
            
        Returns:
            Weighted score
        """
        label_priority = self.label_priority_map.get(prediction.label, 1.0)
        confidence = prediction.confidence
        
        # Evidence strength factor - more supporting tokens and segments increase confidence
        evidence_factor = min(1.0, 0.8 + 0.05 * len(prediction.supporting_tokens) + 
                              0.02 * len(prediction.segment_ids))
        
        # Provider confidence adjustment
        provider_factor = 1.0
        if prediction.provider_context:
            # Known providers get a slight boost
            if prediction.provider_context.get('provider') in ['github', 'gitlab', 'jenkins', 'travis']:
                provider_factor = 1.05
        
        # The final weighted score calculation
        weighted_score = confidence * label_priority * evidence_factor * provider_factor
        
        return weighted_score
        
    def _log_conflict_resolution(self, 
                                competing_predictions: List[RootCausePrediction], 
                                winner: RootCausePrediction) -> None:
        """Log details about conflict resolution for debugging."""
        self.logger.debug(f"Resolved conflict between {len(competing_predictions)} predictions")
        for i, pred in enumerate(competing_predictions):
            score = self.scoring_functions[self.conflict_resolution_strategy](pred)
            is_winner = pred == winner
            self.logger.debug(f"  [{i}] {'✓ ' if is_winner else '  '}Label: {pred.label}, "
                            f"Confidence: {pred.confidence:.2f}, Score: {score:.2f}, "
                            f"Segments: {len(pred.segment_ids)}, Tokens: {len(pred.supporting_tokens)}")

    def enrich_prediction_metadata(self, 
                                  prediction: RootCausePrediction,
                                  segments: List["TokenizedSegment"]) -> RootCausePrediction:
        """
        Enrich prediction with additional contextual metadata from segments.
        
        Args:
            prediction: Prediction to enrich
            segments: All available segments for context
            
        Returns:
            Enriched prediction with additional metadata
        """
        # Create a mapping of segment IDs for quick lookup
        segment_map = {s.id: s for s in segments if hasattr(s, 'id')}
        
        # Collect metadata from all segments involved in this prediction
        section_info = {}
        tokens_by_type = defaultdict(int)
        earliest_line = float('inf')
        latest_line = -1
        
        for seg_id in prediction.segment_ids:
            if seg_id in segment_map:
                segment = segment_map[seg_id]
                
                # Track sections involved
                if hasattr(segment, 'section') and segment.section:
                    section_info[segment.section] = section_info.get(segment.section, 0) + 1
                
                # Track token types
                if hasattr(segment, 'tokens'):
                    for token in segment.tokens:
                        if hasattr(token, 'token_type'):
                            tokens_by_type[token.token_type] += 1
                
                # Track line range
                if hasattr(segment, 'line_number'):
                    earliest_line = min(earliest_line, segment.line_number)
                    latest_line = max(latest_line, segment.line_number)
        
        # Add enriched metadata
        enriched_metadata = dict(prediction.metadata)  # Copy existing metadata
        
        if section_info:
            enriched_metadata['sections'] = dict(section_info)
        
        if tokens_by_type:
            enriched_metadata['token_type_counts'] = dict(tokens_by_type)
        
        if earliest_line < float('inf') and latest_line >= 0:
            enriched_metadata['line_range'] = [earliest_line, latest_line]
        
        # Create new prediction with enriched metadata
        enriched_prediction = RootCausePrediction(
            label=prediction.label,
            confidence=prediction.confidence,
            segment_ids=prediction.segment_ids,
            supporting_tokens=prediction.supporting_tokens,
            provider_context=prediction.provider_context,
            metadata=enriched_metadata,
            classifier_id=prediction.classifier_id
        )
        
        return enriched_prediction
        

class RootCauseAnalysisEngine:
    """
    Complete engine for root cause analysis that manages classifiers and coordinates results.
    """
    
    def __init__(self, confidence_threshold: float = 0.6):
        self.classifier_registry = EnhancedClassifierRegistry()
        self.coordinator = ClassifierCoordinator(base_confidence_threshold=confidence_threshold)
        
    def register_classifier(self, classifier: EnhancedRuleBasedClassifier) -> None:
        """Register a classifier with the engine."""
        self.classifier_registry.register(classifier)
        
    def analyze(self, segments: List["TokenizedSegment"]) -> List[RootCausePrediction]:
        """
        Analyze segments using registered classifiers and coordinate results.
        
        Args:
            segments: List of TokenizedSegment objects to analyze
            
        Returns:
            Coordinated list of root cause predictions
        """
        # Get raw predictions from all classifiers
        raw_predictions = self.classifier_registry.classify(segments)
        
        # Coordinate predictions to resolve conflicts
        coordinated_predictions = self.coordinator.coordinate(raw_predictions)
        
        # Enrich final predictions with additional metadata
        enriched_predictions = [
            self.coordinator.enrich_prediction_metadata(pred, segments)
            for pred in coordinated_predictions
        ]
        
        return enriched_predictions
        
    def batch_analyze(self, batch_segments: List[List["TokenizedSegment"]]) -> List[List[RootCausePrediction]]:
        """
        Process multiple sets of segments.
        
        Args:
            batch_segments: List of lists of segments to analyze
            
        Returns:
            List of lists of predictions for each segment set
        """
        return [self.analyze(segments) for segments in batch_segments]