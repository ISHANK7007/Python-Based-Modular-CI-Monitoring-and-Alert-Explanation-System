from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
from tokenization.token_relationship import TokenizedSegment
class CauseLabelType(Enum):
    """Types of cause labels in multi-label classification."""
    PRIMARY = "primary"       # The main root cause
    SECONDARY = "secondary"   # Contributing factors 
    SYMPTOM = "symptom"       # Resulting effects
    CONTEXT = "context"       # Environmental context


@dataclass
class CauseLabel:
    """A structured cause label with type information and evidence."""
    label: str                                  # The cause label identifier
    label_type: CauseLabelType                  # Type of cause (primary, secondary, etc.)
    confidence: float                           # Confidence score 0.0 to 1.0
    supporting_segment_ids: List[str] = field(default_factory=list)  # Supporting evidence segments
    supporting_tokens: List[str] = field(default_factory=list)       # Supporting tokens/text
    metadata: Dict[str, Any] = field(default_factory=dict)           # Cause-specific metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "label": self.label,
            "label_type": self.label_type.value,
            "confidence": self.confidence,
            "supporting_segment_ids": self.supporting_segment_ids,
            "supporting_tokens": self.supporting_tokens,
            "metadata": self.metadata
        }


@dataclass
class PredictionBundle:
    """
    A bundle of related predictions capturing primary and secondary causes.
    Represents a complete analysis of a CI failure with multiple contributing factors.
    """
    # Core identification
    id: str                                     # Unique identifier for this prediction bundle
    primary_cause: CauseLabel                   # The primary root cause (must have exactly one)
    secondary_causes: List[CauseLabel] = field(default_factory=list)  # Contributing factors (optional)
    symptoms: List[CauseLabel] = field(default_factory=list)          # Resulting effects (optional)
    context_factors: List[CauseLabel] = field(default_factory=list)   # Environmental context (optional)
    
    # Overall bundle metadata
    aggregate_confidence: float = 0.0           # Overall confidence in this analysis
    provider: Optional[str] = None              # CI provider (GitHub, GitLab, etc.)
    job_id: Optional[str] = None                # Associated job identifier
    timestamp: Optional[str] = None             # When this prediction was generated
    classifier_id: Optional[str] = None         # ID of classifier that generated this bundle
    
    # All segment references
    all_segment_references: List["SegmentReference"] = field(default_factory=list)  # All referenced segments
    
    def all_causes(self) -> List[CauseLabel]:
        """Get all causes (primary and secondary) in order of confidence."""
        all_causes = [self.primary_cause] + self.secondary_causes
        return sorted(all_causes, key=lambda c: c.confidence, reverse=True)
    
    def get_supporting_segments(self, include_types: Optional[List[CauseLabelType]] = None) -> Set[str]:
        """Get all unique segment IDs supporting this prediction bundle."""
        segment_ids = set()
        
        # Filter which types of causes to include
        types_to_include = set(include_types) if include_types else {
            CauseLabelType.PRIMARY, CauseLabelType.SECONDARY, 
            CauseLabelType.SYMPTOM, CauseLabelType.CONTEXT
        }
        
        # Add primary cause segments if type is included
        if CauseLabelType.PRIMARY in types_to_include:
            segment_ids.update(self.primary_cause.supporting_segment_ids)
            
        # Add secondary cause segments if type is included
        if CauseLabelType.SECONDARY in types_to_include:
            for cause in self.secondary_causes:
                segment_ids.update(cause.supporting_segment_ids)
                
        # Add symptom segments if type is included
        if CauseLabelType.SYMPTOM in types_to_include:
            for symptom in self.symptoms:
                segment_ids.update(symptom.supporting_segment_ids)
                
        # Add context segments if type is included
        if CauseLabelType.CONTEXT in types_to_include:
            for context in self.context_factors:
                segment_ids.update(context.supporting_segment_ids)
                
        return segment_ids
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "primary_cause": self.primary_cause.to_dict(),
            "secondary_causes": [cause.to_dict() for cause in self.secondary_causes],
            "symptoms": [symptom.to_dict() for symptom in self.symptoms],
            "context_factors": [context.to_dict() for context in self.context_factors],
            "aggregate_confidence": self.aggregate_confidence,
            "provider": self.provider,
            "job_id": self.job_id,
            "timestamp": self.timestamp,
            "classifier_id": self.classifier_id,
            "segment_references": [ref.to_dict() for ref in self.all_segment_references]
        }
    
    @classmethod
    def from_prediction(cls, prediction: RootCausePrediction, segments: List["TokenizedSegment"]) -> "PredictionBundle":
        """Create a prediction bundle from a legacy RootCausePrediction."""
        # Create primary cause
        primary_cause = CauseLabel(
            label=prediction.label,
            label_type=CauseLabelType.PRIMARY,
            confidence=prediction.confidence,
            supporting_segment_ids=prediction.segment_ids,
            supporting_tokens=prediction.supporting_tokens,
            metadata=dict(prediction.metadata)
        )
        
        # Create segment references from prediction
        segment_references = []
        if prediction.segment_references:
            segment_references = prediction.segment_references
        else:
            # Create references from segment IDs and segments
            segment_map = {s.id: s for s in segments if hasattr(s, 'id')}
            for seg_id in prediction.segment_ids:
                if seg_id in segment_map:
                    segment_references.append(SegmentReference.from_segment(segment_map[seg_id]))
        
        # Create bundle
        bundle = cls(
            id=f"bundle_{id(prediction)}",
            primary_cause=primary_cause,
            aggregate_confidence=prediction.confidence,
            classifier_id=prediction.classifier_id,
            all_segment_references=segment_references
        )
        
        # Extract provider and job ID from segment references or provider_context
        if segment_references and hasattr(segment_references[0], 'job_id'):
            bundle.job_id = segment_references[0].job_id
            
        if prediction.provider_context and "provider" in prediction.provider_context:
            bundle.provider = prediction.provider_context["provider"]
            
        return bundle


class MultiLabelClassifier(BaseRootCauseClassifier):
    """
    Base class for multi-label classifiers that predict both primary and secondary causes.
    """
    
    def __init__(self, name: str, confidence_threshold: float = 0.7):
        self.name = name
        self.confidence_threshold = confidence_threshold
        self.classifier_id = f"{self.__class__.__name__}:{id(self)}"
    
    @abstractmethod
    def classify_multi(self, segments: List["TokenizedSegment"]) -> List[PredictionBundle]:
        """
        Classify segments and produce multi-label prediction bundles.
        
        Args:
            segments: List of segments to analyze
            
        Returns:
            List of prediction bundles with primary and secondary causes
        """
        pass
    
    def classify(self, segments: List["TokenizedSegment"]) -> List[RootCausePrediction]:
        """
        Legacy single-label classification method.
        Converts multi-label predictions to traditional single-label format.
        
        Args:
            segments: List of segments to analyze
            
        Returns:
            List of traditional RootCausePrediction objects (primary causes only)
        """
        # Get multi-label predictions
        bundle_predictions = self.classify_multi(segments)
        
        # Convert to legacy format
        legacy_predictions = []
        for bundle in bundle_predictions:
            # Create a segment reference mapping
            seg_ref_map = {ref.segment_id: ref for ref in bundle.all_segment_references}
            
            # Get only the references for primary cause
            primary_references = [
                seg_ref_map[seg_id] 
                for seg_id in bundle.primary_cause.supporting_segment_ids
                if seg_id in seg_ref_map
            ]
            
            # Create legacy prediction
            prediction = RootCausePrediction(
                label=bundle.primary_cause.label,
                confidence=bundle.primary_cause.confidence,
                segment_ids=bundle.primary_cause.supporting_segment_ids,
                segment_references=primary_references,
                supporting_tokens=bundle.primary_cause.supporting_tokens,
                metadata={
                    "has_secondary_causes": len(bundle.secondary_causes) > 0,
                    "bundle_id": bundle.id,
                    "original_metadata": bundle.primary_cause.metadata
                },
                classifier_id=bundle.classifier_id
            )
            
            legacy_predictions.append(prediction)
            
        return legacy_predictions
    
    def batch_classify(self, batch_segments: List[List["TokenizedSegment"]]) -> List[List[RootCausePrediction]]:
        """Process multiple sets of segments."""
        return [self.classify(segments) for segments in batch_segments]
    
    def batch_classify_multi(self, batch_segments: List[List["TokenizedSegment"]]) -> List[List[PredictionBundle]]:
        """Process multiple sets of segments with multi-label classification."""
        return [self.classify_multi(segments) for segments in batch_segments]


class SecondaryCauseDetector:
    """
    Detector for secondary causes that contribute to a primary failure.
    Used by multi-label classifiers to identify contributing factors.
    """
    
    def __init__(self, name: str, label: str, confidence_threshold: float = 0.6):
        self.name = name
        self.label = label
        self.confidence_threshold = confidence_threshold
    
    @abstractmethod
    def detect(self, segments: List["TokenizedSegment"], 
               primary_cause: CauseLabel) -> Optional[CauseLabel]:
        """
        Detect if this secondary cause is present given the primary cause.
        
        Args:
            segments: Segments to analyze
            primary_cause: The primary cause already detected
            
        Returns:
            CauseLabel if this secondary cause is detected, None otherwise
        """
        pass


class PatternBasedSecondaryCauseDetector(SecondaryCauseDetector):
    """
    Secondary cause detector based on regex patterns.
    """
    
    def __init__(self, name: str, label: str, confidence_threshold: float = 0.6):
        super().__init__(name, label, confidence_threshold)
        self.patterns = []
        self._initialize_patterns()
    
    @abstractmethod
    def _initialize_patterns(self):
        """Initialize patterns for this detector."""
        pass
    
    def add_pattern(self, pattern: str, confidence_boost: float = 0.0):
        """Add a pattern to this detector."""
        self.patterns.append((re.compile(pattern, re.IGNORECASE | re.MULTILINE), confidence_boost))
    
    def detect(self, segments: List["TokenizedSegment"], 
               primary_cause: CauseLabel) -> Optional[CauseLabel]:
        """Detect secondary cause based on patterns."""
        matching_segments = []
        supporting_tokens = []
        max_confidence = 0.0
        
        for segment in segments:
            if not hasattr(segment, 'text') or not segment.text:
                continue
                
            for pattern, confidence_boost in self.patterns:
                match = pattern.search(segment.text)
                if match:
                    # Extract matching text
                    matching_text = match.group(0)
                    if matching_text not in supporting_tokens:
                        supporting_tokens.append(matching_text)
                    
                    # Track matching segment
                    if hasattr(segment, 'id') and segment.id not in matching_segments:
                        matching_segments.append(segment.id)
                    
                    # Update max confidence
                    segment_confidence = 0.7 + confidence_boost  # Base confidence + boost
                    if hasattr(segment, 'score'):
                        segment_confidence += segment.score * 0.1  # Boost from segment score
                    
                    max_confidence = max(max_confidence, min(segment_confidence, 0.95))
        
        # If confidence exceeds threshold and we have matches, create cause label
        if max_confidence >= self.confidence_threshold and matching_segments:
            return CauseLabel(
                label=self.label,
                label_type=CauseLabelType.SECONDARY,
                confidence=max_confidence,
                supporting_segment_ids=matching_segments,
                supporting_tokens=supporting_tokens,
                metadata={"detector_name": self.name}
            )
        
        return None


class SymptomDetector:
    """
    Detector for symptoms that result from a primary cause.
    """
    
    def __init__(self, name: str, label: str, confidence_threshold: float = 0.6):
        self.name = name
        self.label = label
        self.confidence_threshold = confidence_threshold
    
    @abstractmethod
    def detect(self, segments: List["TokenizedSegment"], 
               primary_cause: CauseLabel) -> Optional[CauseLabel]:
        """
        Detect if this symptom is present given the primary cause.
        
        Args:
            segments: Segments to analyze
            primary_cause: The primary cause already detected
            
        Returns:
            CauseLabel if this symptom is detected, None otherwise
        """
        pass


class MultiLabelRuleBasedClassifier(MultiLabelClassifier):
    """
    Multi-label classifier implementation using rule-based approach.
    Can detect primary causes, secondary causes, symptoms, and contextual factors.
    """
    
    def __init__(self, name: str, confidence_threshold: float = 0.7):
        super().__init__(name, confidence_threshold)
        self.primary_rules = []  # Rules for primary causes
        self.secondary_detectors = []  # Detectors for secondary causes
        self.symptom_detectors = []  # Detectors for symptoms
        self.context_detectors = []  # Detectors for contextual factors
        self._initialize_rules()
    
    @abstractmethod
    def _initialize_rules(self):
        """Initialize all rules and detectors."""
        pass
    
    def add_primary_rule(self, rule: ContextualRule):
        """Add a rule for primary causes."""
        self.primary_rules.append(rule)
    
    def add_secondary_detector(self, detector: SecondaryCauseDetector):
        """Add a detector for secondary causes."""
        self.secondary_detectors.append(detector)
    
    def add_symptom_detector(self, detector: SymptomDetector):
        """Add a detector for symptoms."""
        self.symptom_detectors.append(detector)
    
    def add_context_detector(self, detector):
        """Add a detector for contextual factors."""
        self.context_detectors.append(detector)
    
    def classify_multi(self, segments: List["TokenizedSegment"]) -> List[PredictionBundle]:
        """Perform multi-label classification."""
        # Generate unique run ID
        run_id = f"run_{id(segments)}_{int(time.time())}"
        
        # Apply primary rules to identify primary causes
        primary_causes = []
        for rule in self.primary_rules:
            rule_results = rule.evaluate(segments)
            
            for primary_segment, context_segments, confidence, supporting_tokens in rule_results:
                if confidence >= self.confidence_threshold:
                    # Create primary cause label
                    segment_ids = [primary_segment.id] + [s.id for s in context_segments if hasattr(s, 'id')]
                    
                    primary_cause = CauseLabel(
                        label=rule.label,
                        label_type=CauseLabelType.PRIMARY,
                        confidence=confidence,
                        supporting_segment_ids=segment_ids,
                        supporting_tokens=supporting_tokens,
                        metadata={"rule_name": rule.name}
                    )
                    
                    primary_causes.append((primary_cause, [primary_segment] + context_segments))
        
        # If no primary causes found, return empty list
        if not primary_causes:
            return []
            
        # Create prediction bundles
        bundles = []
        for primary_cause, cause_segments in primary_causes:
            # Generate bundle ID
            bundle_id = f"bundle_{run_id}_{len(bundles)}"
            
            # Create segment references
            segment_references = [
                SegmentReference.from_segment(seg) 
                for seg in cause_segments
                if hasattr(seg, 'id')
            ]
            
            # Provider and job_id from first segment if available
            provider = None
            job_id = None
            if segment_references:
                job_id = segment_references[0].job_id
                provider = self._extract_provider(cause_segments[0])
            
            # Create initial bundle with just primary cause
            bundle = PredictionBundle(
                id=bundle_id,
                primary_cause=primary_cause,
                aggregate_confidence=primary_cause.confidence,
                provider=provider,
                job_id=job_id,
                timestamp=datetime.utcnow().isoformat(),
                classifier_id=self.classifier_id,
                all_segment_references=segment_references
            )
            
            # Detect secondary causes
            for detector in self.secondary_detectors:
                secondary_cause = detector.detect(segments, primary_cause)
                if secondary_cause:
                    bundle.secondary_causes.append(secondary_cause)
                    
                    # Update segment references
                    self._update_segment_references(
                        bundle, segments, secondary_cause.supporting_segment_ids
                    )
            
            # Detect symptoms
            for detector in self.symptom_detectors:
                symptom = detector.detect(segments, primary_cause)
                if symptom:
                    bundle.symptoms.append(symptom)
                    
                    # Update segment references
                    self._update_segment_references(
                        bundle, segments, symptom.supporting_segment_ids
                    )
            
            # Detect contextual factors
            for detector in self.context_detectors:
                context = detector.detect(segments, primary_cause)
                if context:
                    bundle.context_factors.append(context)
                    
                    # Update segment references
                    self._update_segment_references(
                        bundle, segments, context.supporting_segment_ids
                    )
            
            # Calculate aggregate confidence
            bundle.aggregate_confidence = self._calculate_aggregate_confidence(bundle)
            
            bundles.append(bundle)
        
        # Sort bundles by aggregate confidence
        bundles.sort(key=lambda b: b.aggregate_confidence, reverse=True)
        
        return bundles
    
    def _extract_provider(self, segment: "TokenizedSegment") -> Optional[str]:
        """Extract provider information from a segment."""
        for attr in ['provider', 'provider_name']:
            if hasattr(segment, attr):
                return getattr(segment, attr)
        return None
    
    def _update_segment_references(self, bundle: PredictionBundle, 
                                  segments: List["TokenizedSegment"],
                                  segment_ids: List[str]) -> None:
        """Update segment references in a bundle."""
        # Create mapping of segment IDs to segments
        segment_map = {s.id: s for s in segments if hasattr(s, 'id')}
        
        # Create mapping of segment IDs to existing references
        reference_map = {ref.segment_id: ref for ref in bundle.all_segment_references}
        
        # Add references for new segment IDs
        for seg_id in segment_ids:
            if seg_id not in reference_map and seg_id in segment_map:
                # Create new reference
                new_ref = SegmentReference.from_segment(segment_map[seg_id])
                bundle.all_segment_references.append(new_ref)
                reference_map[seg_id] = new_ref
    
    def _calculate_aggregate_confidence(self, bundle: PredictionBundle) -> float:
        """
        Calculate aggregate confidence for a bundle based on primary and secondary causes.
        
        Primary cause has highest weight, secondary causes boost confidence if they align.
        """
        # Start with primary cause confidence
        primary_confidence = bundle.primary_cause.confidence
        
        # Adjust based on secondary causes
        if bundle.secondary_causes:
            # Average confidence of secondary causes
            secondary_avg = sum(c.confidence for c in bundle.secondary_causes) / len(bundle.secondary_causes)
            
            # Boost if secondary causes have high confidence
            if secondary_avg > 0.7:
                boost = 0.05
            elif secondary_avg > 0.5:
                boost = 0.02
            else:
                boost = 0.0
                
            # More secondary causes provide more evidence (up to a point)
            cause_count_factor = min(0.05, len(bundle.secondary_causes) * 0.01)
            
            # Calculate final confidence
            final_confidence = primary_confidence + boost + cause_count_factor
        else:
            final_confidence = primary_confidence
            
        # Cap at 1.0
        return min(1.0, final_confidence)


# Example implementation

class OutOfMemoryMultiLabelClassifier(MultiLabelRuleBasedClassifier):
    """Multi-label classifier for OOM issues with secondary causes."""
    
    def _initialize_rules(self):
        # Primary rules (similar to those in earlier classifiers)
        java_oom_rule = ContextualRule(
            name="java_oom",
            label="OUT_OF_MEMORY",
            condition=PatternCondition("java\\.lang\\.OutOfMemoryError") & 
                     TokenTypeCondition(['ERROR', 'STACK_TRACE'], min_count=1),
            context_resolver=self._find_stack_traces,
            confidence_calculator=self._oom_confidence,
            token_extractor=self._extract_oom_details
        )
        self.add_primary_rule(java_oom_rule)
        
        # Secondary cause detectors
        large_heap_detector = LargeHeapObjectDetector()
        memory_limit_detector = MemoryLimitDetector()
        gc_overhead_detector = GCOverheadDetector()
        
        self.add_secondary_detector(large_heap_detector)
        self.add_secondary_detector(memory_limit_detector)
        self.add_secondary_detector(gc_overhead_detector)
        
        # Symptom detectors
        process_killed_detector = ProcessKilledSymptomDetector()
        failed_allocation_detector = FailedAllocationSymptomDetector()
        
        self.add_symptom_detector(process_killed_detector)
        self.add_symptom_detector(failed_allocation_detector)
        
        # Context detectors
        container_limits_detector = ContainerLimitsContextDetector()
        jvm_flags_detector = JVMFlagsContextDetector()
        
        self.add_context_detector(container_limits_detector)
        self.add_context_detector(jvm_flags_detector)
    
    def _find_stack_traces(self, segments, segment):
        """Find stack trace segments near the current segment."""
        # ... implementation ...
        return []
    
    def _oom_confidence(self, segment, context_segments):
        """Calculate confidence based on OOM evidence."""
        # ... implementation ...
        return 0.85
    
    def _extract_oom_details(self, segment, context_segments):
        """Extract OOM-specific details."""
        # ... implementation ...
        return ["Java heap space"]


class LargeHeapObjectDetector(PatternBasedSecondaryCauseDetector):
    """Detector for large object allocations causing OOM."""
    
    def __init__(self):
        super().__init__("large_heap_object", "LARGE_OBJECT_ALLOCATION", 0.65)
    
    def _initialize_patterns(self):
        self.add_pattern(r"Failed to allocate a (\d+[KMG]B) \S+ object", 0.1)
        self.add_pattern(r"Could not allocate enough memory for object of size (\d+)", 0.05)


class MemoryLimitDetector(PatternBasedSecondaryCauseDetector):
    """Detector for memory limit configuration issues."""
    
    def __init__(self):
        super().__init__("memory_limit", "MEMORY_LIMIT_TOO_LOW", 0.7)
    
    def _initialize_patterns(self):
        self.add_pattern(r"Limiting container memory to: (\d+[KMG]?)", 0.15)
        self.add_pattern(r"Memory limit set to (\d+[KMG]B)", 0.1)


class ProcessKilledSymptomDetector(PatternBasedSecondaryCauseDetector):
    """Detector for process killed symptoms."""
    
    def __init__(self):
        super().__init__("process_killed", "PROCESS_KILLED", 0.75)
    
    def _initialize_patterns(self):
        self.add_pattern(r"Killed process \d+ \((.*?)\)", 0.2)
        self.add_pattern(r"The process has been killed due to memory pressure", 0.15)


# Enhanced RootCauseAnalysisEngine for multi-label support

class EnhancedRootCauseAnalysisEngine:
    """
    Complete engine for root cause analysis with multi-label support.
    """
    
    def __init__(self, 
                 confidence_threshold: float = 0.65,
                 enable_fallback: bool = True,
                 enable_multi_label: bool = True):
        self.classifier_registry = {}  # Map of name -> classifier
        self.multi_label_registry = {}  # Map of name -> multi-label classifier
        self.confidence_threshold = confidence_threshold
        self.enable_fallback = enable_fallback
        self.enable_multi_label = enable_multi_label
        
        # Fallback classifier
        if enable_fallback:
            self.fallback_classifier = FallbackClassifier(
                confidence_ceiling=confidence_threshold * 0.9
            )
    
    def register_classifier(self, classifier: BaseRootCauseClassifier) -> None:
        """Register a classifier with the engine."""
        if isinstance(classifier, MultiLabelClassifier):
            self.multi_label_registry[classifier.name] = classifier
        else:
            self.classifier_registry[classifier.name] = classifier
    
    def analyze(self, segments: List["TokenizedSegment"]) -> List[RootCausePrediction]:
        """
        Analyze segments using registered classifiers.
        Returns backward-compatible RootCausePrediction objects.
        
        Args:
            segments: TokenizedSegment objects to analyze
            
        Returns:
            List of RootCausePrediction objects
        """
        # Process with multi-label classifiers if enabled
        if self.enable_multi_label and self.multi_label_registry:
            ml_predictions = []
            
            # Apply each multi-label classifier
            for classifier in self.multi_label_registry.values():
                # Get prediction bundles
                bundles = classifier.classify_multi(segments)
                
                # Convert to legacy format
                for bundle in bundles:
                    legacy_pred = self._bundle_to_legacy_prediction(bundle, segments)
                    ml_predictions.append(legacy_pred)
                    
            # If we got predictions from multi-label classifiers, return them
            if ml_predictions:
                return sorted(ml_predictions, key=lambda p: p.confidence, reverse=True)
        
        # Process with traditional classifiers
        predictions = []
        for classifier in self.classifier_registry.values():
            preds = classifier.classify(segments)
            predictions.extend(preds)
        
        # Try fallback if no predictions and fallback is enabled
        if not predictions and self.enable_fallback:
            predictions = self.fallback_classifier.classify(segments)
        
        # Sort by confidence
        predictions.sort(key=lambda p: p.confidence, reverse=True)
        
        return predictions
    
    def analyze_multi_label(self, segments: List["TokenizedSegment"]) -> List[PredictionBundle]:
        """
        Analyze segments using multi-label classifiers.
        Returns PredictionBundle objects with primary and secondary causes.
        
        Args:
            segments: TokenizedSegment objects to analyze
            
        Returns:
            List of PredictionBundle objects
        """
        if not self.enable_multi_label:
            # Convert traditional predictions to bundles
            traditional_preds = self.analyze(segments)
            return [PredictionBundle.from_prediction(pred, segments) for pred in traditional_preds]
        
        # Apply multi-label classifiers
        bundles = []
        for classifier in self.multi_label_registry.values():
            bundles.extend(classifier.classify_multi(segments))
        
        # If no multi-label results, try traditional classifiers and convert
        if not bundles:
            traditional_preds = self.analyze(segments)
            bundles = [PredictionBundle.from_prediction(pred, segments) for pred in traditional_preds]
        
        # Sort by aggregate confidence
        bundles.sort(key=lambda b: b.aggregate_confidence, reverse=True)
        
        return bundles
    
    def _bundle_to_legacy_prediction(self, bundle: PredictionBundle, 
                                    segments: List["TokenizedSegment"]) -> RootCausePrediction:
        """Convert a prediction bundle to legacy format."""
        # Create segment references if needed
        segment_references = []
        if bundle.all_segment_references:
            segment_references = bundle.all_segment_references
        
        # Prepare metadata
        metadata = dict(bundle.primary_cause.metadata)
        
        # Add secondary causes to metadata
        if bundle.secondary_causes:
            metadata["secondary_causes"] = [
                {
                    "label": cause.label,
                    "confidence": cause.confidence,
                    "supporting_tokens": cause.supporting_tokens[:2]  # Limited tokens
                }
                for cause in bundle.secondary_causes
            ]
            
        # Add symptoms to metadata
        if bundle.symptoms:
            metadata["symptoms"] = [
                {
                    "label": symptom.label,
                    "confidence": symptom.confidence
                }
                for symptom in bundle.symptoms
            ]
            
        # Add context factors to metadata
        if bundle.context_factors:
            metadata["context_factors"] = [
                {
                    "label": context.label,
                    "confidence": context.confidence
                }
                for context in bundle.context_factors
            ]
            
        # Create legacy prediction
        prediction = RootCausePrediction(
            label=bundle.primary_cause.label,
            confidence=bundle.primary_cause.confidence,
            segment_ids=bundle.primary_cause.supporting_segment_ids,
            segment_references=segment_references,
            supporting_tokens=bundle.primary_cause.supporting_tokens,
            provider_context={"provider": bundle.provider} if bundle.provider else {},
            metadata=metadata,
            classifier_id=bundle.classifier_id
        )
        
        return prediction