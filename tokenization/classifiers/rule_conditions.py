from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Pattern, Set, Tuple, Callable
import re
from dataclasses import dataclass, field
from enum import Enum

from core.root_cause_prediction import RootCausePrediction
from tokenization.models import TokenizedSegment
from tokenization.classifiers.rule_based_classifier import BaseRootCauseClassifier

class RuleCondition:
    """Base class for rule conditions that can be combined with boolean logic."""
    
    def __init__(self):
        pass
        
    @abstractmethod
    def evaluate(self, segment: "TokenizedSegment") -> bool:
        """Evaluate if the condition is met for a given segment."""
        pass
    
    def __and__(self, other: "RuleCondition") -> "AndCondition":
        return AndCondition(self, other)
    
    def __or__(self, other: "RuleCondition") -> "OrCondition":
        return OrCondition(self, other)
    
    def __invert__(self) -> "NotCondition":
        return NotCondition(self)


class AndCondition(RuleCondition):
    """Logical AND of two conditions."""
    
    def __init__(self, left: RuleCondition, right: RuleCondition):
        super().__init__()
        self.left = left
        self.right = right
        
    def evaluate(self, segment: "TokenizedSegment") -> bool:
        return self.left.evaluate(segment) and self.right.evaluate(segment)


class OrCondition(RuleCondition):
    """Logical OR of two conditions."""
    
    def __init__(self, left: RuleCondition, right: RuleCondition):
        super().__init__()
        self.left = left
        self.right = right
        
    def evaluate(self, segment: "TokenizedSegment") -> bool:
        return self.left.evaluate(segment) or self.right.evaluate(segment)


class NotCondition(RuleCondition):
    """Logical NOT of a condition."""
    
    def __init__(self, condition: RuleCondition):
        super().__init__()
        self.condition = condition
        
    def evaluate(self, segment: "TokenizedSegment") -> bool:
        return not self.condition.evaluate(segment)


class PatternCondition(RuleCondition):
    """Condition that checks if segment text matches a regex pattern."""
    
    def __init__(self, pattern: str):
        super().__init__()
        self.pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        
    def evaluate(self, segment: "TokenizedSegment") -> bool:
        return bool(self.pattern.search(segment.text))
    
    def extract_tokens(self, segment: "TokenizedSegment") -> List[str]:
        """Extract supporting tokens based on this pattern."""
        match = self.pattern.search(segment.text)
        if not match:
            return []
        
        # Default extraction: return the matched text
        return [match.group(0)]


class TokenTypeCondition(RuleCondition):
    """Condition that checks if segment contains specific token types."""
    
    def __init__(self, token_types: List[str], min_count: int = 1, percentage: Optional[float] = None):
        super().__init__()
        self.token_types = set(token_types)
        self.min_count = min_count
        self.percentage = percentage
        
    def evaluate(self, segment: "TokenizedSegment") -> bool:
        if not hasattr(segment, 'tokens') or not segment.tokens:
            return False
            
        matching_tokens = [t for t in segment.tokens if t.token_type in self.token_types]
        
        if self.percentage is not None:
            # Check if percentage of tokens of specified type exceeds threshold
            if not segment.tokens:
                return False
            percentage = len(matching_tokens) / len(segment.tokens)
            return percentage >= self.percentage
        else:
            # Check if count of tokens of specified type exceeds threshold
            return len(matching_tokens) >= self.min_count


class SectionCondition(RuleCondition):
    """Condition that checks if segment belongs to a specific section."""
    
    def __init__(self, section_patterns: List[str]):
        super().__init__()
        self.section_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in section_patterns]
        
    def evaluate(self, segment: "TokenizedSegment") -> bool:
        if not hasattr(segment, 'section') or not segment.section:
            return False
            
        for pattern in self.section_patterns:
            if pattern.search(segment.section):
                return True
        return False


class StreamCondition(RuleCondition):
    """Condition that checks if segment belongs to a specific stream (stdout/stderr)."""
    
    def __init__(self, stream_names: List[str]):
        super().__init__()
        self.stream_names = set(stream_names)
        
    def evaluate(self, segment: "TokenizedSegment") -> bool:
        if not hasattr(segment, 'stream') or not segment.stream:
            return False
        return segment.stream in self.stream_names


class ContextCondition(RuleCondition):
    """Condition that checks if related segments in context satisfy a condition."""
    
    def __init__(self, relative_segments_condition: Callable[["TokenizedSegment", List["TokenizedSegment"]], bool]):
        super().__init__()
        self.condition_fn = relative_segments_condition
        
    def evaluate(self, segment: "TokenizedSegment") -> bool:
        # This requires a segment context to be provided
        if not hasattr(segment, 'context') or not segment.context:
            return False
            
        return self.condition_fn(segment, segment.context)


class ContextualRule:
    """A rule that can evaluate conditions across multiple related segments."""
    
    def __init__(self, name: str, label: str, condition: RuleCondition, 
                 context_resolver: Callable[[List["TokenizedSegment"], "TokenizedSegment"], List["TokenizedSegment"]],
                 confidence_calculator: Callable[["TokenizedSegment", List["TokenizedSegment"]], float],
                 token_extractor: Optional[Callable[["TokenizedSegment", List["TokenizedSegment"]], List[str]]] = None):
        self.name = name
        self.label = label
        self.condition = condition
        self.context_resolver = context_resolver
        self.confidence_calculator = confidence_calculator
        self.token_extractor = token_extractor or (lambda s, ctx: [])
        
    def evaluate(self, segments: List["TokenizedSegment"]) -> List[Tuple["TokenizedSegment", List["TokenizedSegment"], float, List[str]]]:
        """
        Evaluate this rule across a list of segments, finding matches and calculating confidence.
        
        Returns:
            List of tuples: (matching_segment, context_segments, confidence, supporting_tokens)
        """
        results = []
        
        for i, segment in enumerate(segments):
            if self.condition.evaluate(segment):
                # Find related segments using the context resolver
                context_segments = self.context_resolver(segments, segment)
                
                # Calculate confidence
                confidence = self.confidence_calculator(segment, context_segments)
                
                # Extract supporting tokens
                supporting_tokens = self.token_extractor(segment, context_segments)
                
                results.append((segment, context_segments, confidence, supporting_tokens))
                
        return results


class EnhancedRuleBasedClassifier(BaseRootCauseClassifier):
    """Enhanced classifier that supports contextual rules with metadata awareness."""
    
    def __init__(self, name: str, confidence_threshold: float = 0.7):
        self.name = name
        self.confidence_threshold = confidence_threshold
        self.classifier_id = f"{self.__class__.__name__}:{id(self)}"
        self.rules: List[ContextualRule] = []
        self._initialize_rules()
    
    @abstractmethod
    def _initialize_rules(self) -> None:
        """Initialize classification rules."""
        pass
        
    def add_rule(self, rule: ContextualRule) -> None:
        """Add a rule to this classifier."""
        self.rules.append(rule)
    
    def classify(self, segments: List["TokenizedSegment"]) -> List[RootCausePrediction]:
        """Apply all rules to segments and generate predictions."""
        predictions = []
        
        # Preprocess: ensure all segments have IDs
        for i, segment in enumerate(segments):
            if not hasattr(segment, 'id') or not segment.id:
                segment.id = f"segment_{i}"
        
        # Apply all rules
        for rule in self.rules:
            rule_results = rule.evaluate(segments)
            
            for primary_segment, context_segments, confidence, supporting_tokens in rule_results:
                if confidence >= self.confidence_threshold:
                    # Create provider context with segment metadata
                    provider_context = self._extract_provider_context(primary_segment)
                    
                    # Collect all segment IDs involved in this prediction
                    segment_ids = [primary_segment.id] + [s.id for s in context_segments]
                    
                    # Create prediction
                    prediction = RootCausePrediction(
                        label=rule.label,
                        confidence=confidence,
                        segment_ids=segment_ids,
                        supporting_tokens=supporting_tokens,
                        provider_context=provider_context,
                        metadata={
                            "rule_name": rule.name,
                            "primary_segment_section": getattr(primary_segment, 'section', None),
                            "primary_segment_stream": getattr(primary_segment, 'stream', None),
                        },
                        classifier_id=self.classifier_id
                    )
                    
                    predictions.append(prediction)
        
        # Sort by confidence (highest first)
        predictions.sort(key=lambda p: p.confidence, reverse=True)
        return predictions
    
    def batch_classify(self, batch_segments: List[List["TokenizedSegment"]]) -> List[List[RootCausePrediction]]:
        """Classify batches of segments."""
        return [self.classify(segments) for segments in batch_segments]
    
    def _extract_provider_context(self, segment: "TokenizedSegment") -> Dict[str, Any]:
        """Extract provider-specific context from the segment."""
        context = {}
        
        for attr in ['provider', 'provider_name', 'provider_version', 'provider_config']:
            if hasattr(segment, attr):
                context[attr] = getattr(segment, attr)
                
        return context


# Example usage with cross-token joins

class BuildFailureClassifier(EnhancedRuleBasedClassifier):
    """Classifier for build failures with rich metadata support."""
    
    def _initialize_rules(self):
        # Define common context resolvers
        def same_section_resolver(segments, segment):
            """Find segments in the same section as the given segment."""
            if not hasattr(segment, 'section') or not segment.section:
                return []
                
            return [s for s in segments if hasattr(s, 'section') 
                    and s.section == segment.section 
                    and s != segment]
        
        def exit_code_resolver(segments, segment):
            """Find exit code segments near the current segment."""
            if not hasattr(segment, 'line_number'):
                return []
                
            # Look for exit code segments within 10 lines after this segment
            exit_code_segments = []
            for s in segments:
                if (hasattr(s, 'line_number') and hasattr(s, 'tokens') and
                    s.line_number > segment.line_number and 
                    s.line_number <= segment.line_number + 10):
                    # Check if segment contains exit code tokens
                    has_exit_code = any(t.token_type == 'EXIT_CODE' for t in s.tokens)
                    if has_exit_code:
                        exit_code_segments.append(s)
            
            return exit_code_segments[:1]  # Just return the first one found
        
        # Define confidence calculators
        def basic_confidence(segment, context_segments):
            """Basic confidence calculation."""
            base_confidence = 0.8
            
            # Boost confidence based on segment score if available
            if hasattr(segment, 'score'):
                base_confidence = min(base_confidence + segment.score * 0.2, 1.0)
                
            return base_confidence
        
        def error_with_exit_code_confidence(segment, context_segments):
            """Higher confidence when both error message and exit code are present."""
            base_confidence = 0.8
            
            # Boost for non-zero exit codes in context
            if context_segments:
                base_confidence += 0.15
                
            # Boost for high segment score
            if hasattr(segment, 'score'):
                base_confidence = min(base_confidence + segment.score * 0.05, 1.0)
                
            return base_confidence
        
        # Define token extractors
        def extract_error_text(segment, context_segments):
            """Extract error text from segment."""
            result = []
            if hasattr(segment, 'tokens'):
                error_tokens = [t.text for t in segment.tokens 
                               if hasattr(t, 'token_type') and t.token_type == 'ERROR']
                if error_tokens:
                    result.extend(error_tokens[:3])  # Limit to first 3 for brevity
            
            # Add exit code if available
            for s in context_segments:
                if hasattr(s, 'tokens'):
                    exit_tokens = [t.text for t in s.tokens 
                                  if hasattr(t, 'token_type') and t.token_type == 'EXIT_CODE']
                    if exit_tokens:
                        result.extend(exit_tokens)
            
            return result
            
        # Create complex conditions using the condition classes
        compilation_error = PatternCondition("compilation failed|javac error|error: could not compile") & \
                           TokenTypeCondition(['ERROR', 'COMMAND'], min_count=1) & \
                           StreamCondition(['stderr'])
        
        exit_code_condition = TokenTypeCondition(['EXIT_CODE']) & \
                              PatternCondition("exit (code|status): ([1-9][0-9]*)")
        
        # Add rules
        self.add_rule(ContextualRule(
            name="compilation_error_with_exit_code",
            label="BUILD_FAILURE",
            condition=compilation_error,
            context_resolver=exit_code_resolver,
            confidence_calculator=error_with_exit_code_confidence,
            token_extractor=extract_error_text
        ))
        
        self.add_rule(ContextualRule(
            name="maven_build_failure",
            label="BUILD_FAILURE",
            condition=PatternCondition("\\[ERROR\\] Failed to execute goal .* compile") & 
                     SectionCondition(["build", "maven"]),
            context_resolver=same_section_resolver,
            confidence_calculator=basic_confidence,
            token_extractor=lambda s, ctx: [match.group(0) for match in 
                                           re.finditer(r"\[ERROR\] Failed to execute goal ([^:]+)", s.text)]
        ))


class OutOfMemoryClassifier(EnhancedRuleBasedClassifier):
    """Classifier for out of memory errors with metadata support."""
    
    def _initialize_rules(self):
        # Java OOM detection with stack trace
        java_oom_condition = PatternCondition("java\\.lang\\.OutOfMemoryError") & \
                            TokenTypeCondition(['ERROR', 'STACK_TRACE'], min_count=1)
                            
        # Define context resolver to find stack traces
        def find_stack_traces(segments, segment):
            """Find stack trace segments near the current segment."""
            if not hasattr(segment, 'line_number'):
                return []
                
            # Look for stack trace segments within 20 lines after this segment
            stack_segments = []
            for s in segments:
                if (hasattr(s, 'line_number') and hasattr(s, 'tokens') and
                    abs(s.line_number - segment.line_number) <= 20):
                    # Check if segment contains stack trace tokens
                    has_stack = any(t.token_type == 'STACK_TRACE' for t in s.tokens)
                    if has_stack and s != segment:
                        stack_segments.append(s)
            
            return stack_segments
        
        # Extract OOM-specific tokens
        def extract_oom_details(segment, context_segments):
            """Extract OOM-specific details from segment and context."""
            results = []
            
            # Extract heap size if available
            heap_match = re.search(r"Java heap space|GC overhead limit exceeded", segment.text)
            if heap_match:
                results.append(heap_match.group(0))
                
            # Extract memory limits if available
            mem_match = re.search(r"(\d+[KMG]B?)", segment.text)
            if mem_match:
                results.append(f"Memory: {mem_match.group(1)}")
                
            return results
        
        # Calculate confidence based on supporting evidence
        def oom_confidence(segment, context_segments):
            """Calculate confidence based on OOM evidence."""
            # Start with base confidence
            confidence = 0.85
            
            # Boost confidence if we have stack traces
            if context_segments:
                confidence += 0.1
                
            # Boost if we have memory size information
            if re.search(r"(\d+[KMG]B?)", segment.text):
                confidence += 0.05
                
            return min(confidence, 1.0)
              
        # Add rules
        self.add_rule(ContextualRule(
            name="java_oom_with_stack",
            label="OUT_OF_MEMORY",
            condition=java_oom_condition,
            context_resolver=find_stack_traces,
            confidence_calculator=oom_confidence,
            token_extractor=extract_oom_details
        ))
        
        # Process killed OOM detection
        process_killed_condition = PatternCondition(r"Killed\s+.*\s+\(Out of memory\)") | \
                                  (PatternCondition(r"Killed") & TokenTypeCondition(['ERROR', 'SYSTEM_EVENT']))
                                  
        self.add_rule(ContextualRule(
            name="process_killed_oom",
            label="OUT_OF_MEMORY",
            condition=process_killed_condition,
            context_resolver=lambda segments, segment: [],  # No additional context needed
            confidence_calculator=lambda segment, ctx: 0.9,  # High confidence for explicit OOM kills
            token_extractor=lambda segment, ctx: ["Process killed", "OOM"]
        ))


# Registry to manage all available classifiers
class EnhancedClassifierRegistry:
    """Registry for enhanced classifiers with metadata support."""
    
    def __init__(self):
        self.classifiers: Dict[str, EnhancedRuleBasedClassifier] = {}
    
    def register(self, classifier: EnhancedRuleBasedClassifier) -> None:
        """Register a classifier with the registry."""
        self.classifiers[classifier.name] = classifier
    
    def classify(self, segments: List["TokenizedSegment"]) -> List[RootCausePrediction]:
        """Apply all registered classifiers and return aggregated results."""
        all_predictions = []
        for classifier in self.classifiers.values():
            predictions = classifier.classify(segments)
            all_predictions.extend(predictions)
        
        # Sort by confidence (highest first)
        all_predictions.sort(key=lambda p: p.confidence, reverse=True)
        return all_predictions