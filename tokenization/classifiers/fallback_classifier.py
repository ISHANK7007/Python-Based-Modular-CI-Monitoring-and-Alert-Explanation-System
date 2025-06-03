from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
import re
import logging
from collections import Counter, defaultdict

from core.root_cause_prediction import RootCausePrediction
from tokenization.models import TokenizedSegment
from tokenization.classifiers.registry_setup import EnhancedClassifierRegistry, EnhancedRuleBasedClassifier
from tokenization.classifiers.classifier_coordinator import ClassifierCoordinator


class FallbackClassifier:
    """
    Fallback classifier that activates when no explicit rules match.
    Performs heuristic analysis to provide best-effort classification with diagnostic information.
    """
    
    def __init__(self, 
                 confidence_ceiling: float = 0.6,  # Maximum confidence for fallback predictions
                 enable_heuristics: bool = True,   # Enable heuristic label suggestions
                 min_segment_score: float = 0.4):  # Minimum segment score to consider
        self.confidence_ceiling = confidence_ceiling
        self.enable_heuristics = enable_heuristics
        self.min_segment_score = min_segment_score
        self.classifier_id = "FallbackClassifier"
        
        # Heuristic patterns for common issues
        self.heuristic_patterns = [
            (r"permission denied|access denied|not authorized", "PERMISSION_DENIED"),
            (r"out of memory|java\.lang\.OutOfMemoryError|Killed.*\(Out of memory\)", "OUT_OF_MEMORY"),
            (r"No such file or directory|file not found|cannot find|missing file", "MISSING_FILE"),
            (r"connection timed out|deadline exceeded|operation timed out", "TIMEOUT"),
            (r"curl: \(\d+\)|wget: .*failed|unable to download", "DOWNLOAD_FAILURE"),
            (r"syntax error|unexpected token|unexpected end of input", "SYNTAX_ERROR"),
            (r"version conflict|incompatible version|wrong version", "VERSION_CONFLICT"),
            (r"config(?:uration)? (?:invalid|error|incorrect)", "CONFIGURATION_ERROR"),
            (r"not enough (?:disk|space)|no space left on device", "DISK_SPACE"),
            (r"network (?:error|unreachable|failure)|failed to connect", "NETWORK_ERROR")
        ]
        
    def classify(self, segments: List["TokenizedSegment"]) -> List[RootCausePrediction]:
        """
        Generate fallback classifications for high-scoring segments when no explicit rules match.
        
        Args:
            segments: Tokenized segments to analyze
            
        Returns:
            List of fallback RootCausePrediction objects
        """
        if not segments:
            return []
            
        # Filter for high-scoring segments
        significant_segments = [
            s for s in segments 
            if hasattr(s, 'score') and s.score >= self.min_segment_score
        ]
        
        # If no significant segments, use highest scoring segments (up to 3)
        if not significant_segments:
            scored_segments = [
                (s, getattr(s, 'score', 0.0)) for s in segments
            ]
            scored_segments.sort(key=lambda x: x[1], reverse=True)
            significant_segments = [s for s, _ in scored_segments[:3]]
        
        # Generate fallback predictions
        predictions = []
        for segment in significant_segments:
            # Try to identify a likely root cause label
            label, heuristic_confidence = self._suggest_label(segment)
            
            # Calculate base confidence (lower than normal classifiers)
            base_confidence = min(
                self.confidence_ceiling,  # Cap at ceiling
                0.3 + (getattr(segment, 'score', 0.5) * 0.3)  # Base + segment score boost
            )
            
            # Adjust confidence based on heuristic match
            adjusted_confidence = base_confidence
            if label != "UNCLASSIFIED":
                adjusted_confidence = min(
                    self.confidence_ceiling,
                    base_confidence + (heuristic_confidence * 0.2)
                )
                
            # Extract diagnostic information
            supporting_tokens = self._extract_diagnostic_tokens(segment)
            
            # Create prediction
            prediction = RootCausePrediction(
                label=label,
                confidence=adjusted_confidence,
                segment_ids=[getattr(segment, 'id', f"segment_{id(segment)}")],
                supporting_tokens=supporting_tokens,
                provider_context=self._extract_provider_context(segment),
                metadata={
                    "is_fallback": True,
                    "fallback_reason": "no_explicit_rule_match",
                    "segment_score": getattr(segment, 'score', 0.0),
                    "diagnostic_info": self._generate_diagnostic_info(segment)
                },
                classifier_id=self.classifier_id
            )
            
            predictions.append(prediction)
            
        # Sort by confidence and return
        predictions.sort(key=lambda p: p.confidence, reverse=True)
        return predictions[:3]  # Limit to top 3 fallback predictions
        
    def _suggest_label(self, segment: "TokenizedSegment") -> Tuple[str, float]:
        """
        Suggest a root cause label based on heuristic pattern matching.
        
        Args:
            segment: Segment to analyze
            
        Returns:
            Tuple of (suggested_label, confidence_adjustment)
        """
        if not self.enable_heuristics or not hasattr(segment, 'text') or not segment.text:
            return "UNCLASSIFIED", 0.0
            
        best_label = "UNCLASSIFIED"
        best_confidence = 0.0
        
        # Try matching heuristic patterns
        for pattern, label in self.heuristic_patterns:
            match = re.search(pattern, segment.text, re.IGNORECASE)
            if match:
                # Calculate match quality
                match_span = match.span()
                match_length = match_span[1] - match_span[0]
                match_ratio = match_length / len(segment.text)
                
                # More specific matches and better coverage get higher confidence
                confidence = 0.4 + (match_ratio * 0.3) + (0.3 if label != "UNCLASSIFIED" else 0)
                
                # Keep the highest confidence match
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_label = label
        
        # Analyze token types if we didn't find a good match
        if best_label == "UNCLASSIFIED" and hasattr(segment, 'tokens'):
            token_types = Counter(t.token_type for t in segment.tokens if hasattr(t, 'token_type'))
            
            # Suggest labels based on token type patterns
            if token_types.get('ERROR', 0) > 0 and token_types.get('COMMAND', 0) > 0:
                best_label = "COMMAND_FAILURE"
                best_confidence = 0.3
            elif token_types.get('ERROR', 0) > 0 and token_types.get('STACK_TRACE', 0) > 0:
                best_label = "RUNTIME_ERROR"
                best_confidence = 0.4
            elif token_types.get('WARNING', 0) > 3:  # Multiple warnings
                best_label = "CONFIGURATION_WARNING"
                best_confidence = 0.25
                
        return best_label, best_confidence
        
    def _extract_diagnostic_tokens(self, segment: "TokenizedSegment") -> List[str]:
        """
        Extract diagnostic tokens from a segment for fallback prediction.
        
        Args:
            segment: Segment to analyze
            
        Returns:
            List of diagnostic token strings
        """
        diagnostics = []
        
        # Extract most important tokens
        if hasattr(segment, 'tokens'):
            # Collect error and warning messages
            error_tokens = [
                t.text for t in segment.tokens 
                if hasattr(t, 'token_type') and t.token_type in ['ERROR', 'EXCEPTION'] and hasattr(t, 'text')
            ]
            diagnostics.extend(error_tokens[:2])  # Limit to top 2
            
            # If no errors, try warnings
            if not error_tokens:
                warning_tokens = [
                    t.text for t in segment.tokens 
                    if hasattr(t, 'token_type') and t.token_type == 'WARNING' and hasattr(t, 'text')
                ]
                diagnostics.extend(warning_tokens[:2])
                
            # Add exit codes if present
            exit_tokens = [
                t.text for t in segment.tokens 
                if hasattr(t, 'token_type') and t.token_type == 'EXIT_CODE' and hasattr(t, 'text')
            ]
            diagnostics.extend(exit_tokens[:1])
            
        # If no tokens or no diagnostic tokens, extract from text
        if not diagnostics and hasattr(segment, 'text') and segment.text:
            # Try to extract error-like patterns
            error_matches = re.findall(r'(?:error|exception|fatal|failed): ([^\n]{5,100})', 
                                     segment.text, re.IGNORECASE)
            if error_matches:
                diagnostics.extend(error_matches[:2])
                
            # Try to find line/column references
            line_matches = re.findall(r'(?:line|at) (\d+)(?::(\d+))?', segment.text)
            if line_matches:
                diagnostics.append(f"at line {line_matches[0][0]}")
                
        # If still no diagnostics, use a snippet of text
        if not diagnostics and hasattr(segment, 'text') and segment.text:
            # Take a reasonable text snippet (first 100 chars)
            snippet = segment.text[:100].strip()
            if snippet:
                diagnostics.append(snippet + ("..." if len(segment.text) > 100 else ""))
                
        return diagnostics
                
    def _extract_provider_context(self, segment: "TokenizedSegment") -> Dict[str, Any]:
        """Extract provider context information from segment."""
        context = {}
        
        for attr in ['provider', 'provider_name', 'provider_version']:
            if hasattr(segment, attr):
                context[attr] = getattr(segment, attr)
                
        return context
        
    def _generate_diagnostic_info(self, segment: "TokenizedSegment") -> Dict[str, Any]:
        """
        Generate detailed diagnostic information for fallback classification.
        
        Args:
            segment: Segment to analyze
            
        Returns:
            Dictionary with diagnostic metadata
        """
        diagnostics = {}
        
        # Section information
        if hasattr(segment, 'section'):
            diagnostics['section'] = segment.section
            
        # Line information
        if hasattr(segment, 'line_number'):
            diagnostics['line_number'] = segment.line_number
            
        # Stream information
        if hasattr(segment, 'stream'):
            diagnostics['stream'] = segment.stream
            
        # Token type distribution
        if hasattr(segment, 'tokens'):
            token_counter = Counter(t.token_type for t in segment.tokens if hasattr(t, 'token_type'))
            if token_counter:
                diagnostics['token_types'] = dict(token_counter.most_common(5))
                
        # Length/size information
        if hasattr(segment, 'text'):
            diagnostics['text_length'] = len(segment.text)
            diagnostics['line_count'] = segment.text.count('\n') + 1
                
        return diagnostics


class RootCauseAnalysisEngine:
    """Complete engine for root cause analysis with fallback mechanism."""
    
    def __init__(self, 
                 confidence_threshold: float = 0.65,
                 enable_fallback: bool = True,
                 fallback_confidence_ceiling: float = 0.6):
        self.classifier_registry = EnhancedClassifierRegistry()
        self.coordinator = ClassifierCoordinator(
            base_confidence_threshold=confidence_threshold
        )
        
        # Fallback classifier for when no rules match
        self.enable_fallback = enable_fallback
        self.fallback_classifier = FallbackClassifier(
            confidence_ceiling=fallback_confidence_ceiling
        )
        
    def register_classifier(self, classifier: EnhancedRuleBasedClassifier) -> None:
        """Register a classifier with the engine."""
        self.classifier_registry.register(classifier)
        
    def analyze(self, segments: List["TokenizedSegment"]) -> List[RootCausePrediction]:
        """
        Analyze segments using registered classifiers and coordinate results.
        Falls back to heuristic classification when no explicit rules match.
        
        Args:
            segments: List of TokenizedSegment objects to analyze
            
        Returns:
            Coordinated list of root cause predictions
        """
        # Get raw predictions from all classifiers
        raw_predictions = self.classifier_registry.classify(segments)
        
        # Generate fallback predictions if enabled and no predictions matched
        if self.enable_fallback and not raw_predictions:
            fallback_predictions = self.fallback_classifier.classify(segments)
            raw_predictions.extend(fallback_predictions)
            
        # If still no predictions, generate a single UNCLASSIFIED prediction
        if not raw_predictions:
            # Find highest-scoring segment
            best_segment = None
            best_score = -1
            for s in segments:
                score = getattr(s, 'score', 0)
                if score > best_score:
                    best_score = score
                    best_segment = s
                    
            if best_segment:
                # Generate basic unclassified prediction
                basic_prediction = RootCausePrediction(
                    label="UNCLASSIFIED",
                    confidence=0.3,  # Very low confidence
                    segment_ids=[getattr(best_segment, 'id', f"segment_{id(best_segment)}")],
                    supporting_tokens=[],
                    provider_context={},
                    metadata={
                        "is_fallback": True,
                        "fallback_reason": "last_resort",
                        "diagnostic_info": {
                            "message": "No classification rules matched and heuristics failed."
                        }
                    },
                    classifier_id="LastResortFallback"
                )
                raw_predictions.append(basic_prediction)
        
        # Coordinate predictions to resolve conflicts
        coordinated_predictions = self.coordinator.coordinate(raw_predictions)
        
        # Enrich final predictions with additional metadata
        enriched_predictions = [
            self.coordinator.enrich_prediction_metadata(pred, segments)
            for pred in coordinated_predictions
        ]
        
        return enriched_predictions