from typing import List, Dict, Any, Optional, NamedTuple
from dataclasses import dataclass, field
from datetime import datetime
from tokenization.token_relationship import TokenizedSegment
@dataclass
class SegmentReference:
    """Rich reference to a log segment with full context information."""
    segment_id: str
    job_id: Optional[str] = None
    section: Optional[str] = None
    step_name: Optional[str] = None
    line_range: Optional[List[int]] = None
    timestamp_range: Optional[List[str]] = None
    file_path: Optional[str] = None
    stream: Optional[str] = None
    url: Optional[str] = None
    context_hash: Optional[str] = None  # Hash to reference segments in external storage
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {k: v for k, v in self.__dict__.items() if v is not None}
    
    @classmethod
    def from_segment(cls, segment: "TokenizedSegment") -> "SegmentReference":
        """Create a reference from a TokenizedSegment object."""
        ref = cls(segment_id=getattr(segment, 'id', f"segment_{id(segment)}"))
        
        # Copy attributes from segment if they exist
        for attr in ['job_id', 'section', 'step_name', 'stream', 'file_path', 'context_hash']:
            if hasattr(segment, attr):
                setattr(ref, attr, getattr(segment, attr))
        
        # Handle line range
        if hasattr(segment, 'line_number'):
            start_line = segment.line_number
            end_line = start_line
            if hasattr(segment, 'text'):
                # Calculate end line based on newlines in text
                end_line = start_line + segment.text.count('\n')
            ref.line_range = [start_line, end_line]
        
        # Handle timestamps if available
        if hasattr(segment, 'timestamp'):
            ref.timestamp_range = [segment.timestamp, segment.timestamp]
        elif hasattr(segment, 'timestamp_range'):
            ref.timestamp_range = segment.timestamp_range
            
        # Generate URL if we have enough information
        ref.url = cls._generate_url(segment)
        
        return ref
    
    @staticmethod
    def _generate_url(segment: "TokenizedSegment") -> Optional[str]:
        """Generate a URL to the exact log location if possible."""
        # Skip if we don't have provider info
        if not hasattr(segment, 'provider') or not segment.provider:
            return None
            
        provider = segment.provider.lower()
        
        # GitHub Actions URL
        if provider == 'github' and hasattr(segment, 'job_id') and hasattr(segment, 'run_id'):
            repo = getattr(segment, 'repository', '')
            if repo and segment.job_id and segment.run_id:
                return f"https://github.com/{repo}/actions/runs/{segment.run_id}/jobs/{segment.job_id}#step:{getattr(segment, 'step_id', '')}"
                
        # GitLab CI URL
        elif provider == 'gitlab' and hasattr(segment, 'job_id') and hasattr(segment, 'pipeline_id'):
            project_id = getattr(segment, 'project_id', '')
            if project_id and segment.job_id and segment.pipeline_id:
                return f"https://gitlab.com/api/v4/projects/{project_id}/pipelines/{segment.pipeline_id}/jobs/{segment.job_id}"
                
        # Jenkins URL
        elif provider == 'jenkins' and hasattr(segment, 'build_url'):
            return segment.build_url + "console"
            
        # Travis CI URL
        elif provider == 'travis' and hasattr(segment, 'job_id') and hasattr(segment, 'build_id'):
            return f"https://travis-ci.org/builds/{segment.build_id}/jobs/{segment.job_id}"
            
        return None


@dataclass
class RootCausePrediction:
    """Enhanced structured output for root cause classification with segment references."""
    label: str  # The predicted root cause label
    confidence: float  # Confidence score between 0.0 and 1.0
    segment_ids: List[str]  # IDs of segments that contributed to this prediction
    
    # Detailed segment references with full context
    segment_references: List[SegmentReference] = field(default_factory=list)
    
    supporting_tokens: List[str] = field(default_factory=list)  # Key tokens that influenced the prediction
    provider_context: Dict[str, Any] = field(default_factory=dict)  # Provider-specific context
    metadata: Dict[str, Any] = field(default_factory=dict)  # General metadata
    classifier_id: Optional[str] = None  # Classifier signature for audit tracking
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation, suitable for JSON serialization."""
        result = {
            "label": self.label,
            "confidence": self.confidence,
            "segment_ids": self.segment_ids,
            "segment_references": [ref.to_dict() for ref in self.segment_references],
            "supporting_tokens": self.supporting_tokens,
            "metadata": self.metadata
        }
        
        if self.provider_context:
            result["provider_context"] = self.provider_context
            
        if self.classifier_id:
            result["classifier_id"] = self.classifier_id
            
        return result
    
    @classmethod
    def from_prediction(cls, prediction: "RootCausePrediction", 
                        segments: List["TokenizedSegment"]) -> "RootCausePrediction":
        """Create a new prediction with enhanced segment references."""
        # Create a mapping of segment IDs for quick lookup
        segment_map = {s.id: s for s in segments if hasattr(s, 'id')}
        
        # Generate segment references
        references = []
        for seg_id in prediction.segment_ids:
            if seg_id in segment_map:
                references.append(SegmentReference.from_segment(segment_map[seg_id]))
        
        # Create a new prediction with segment references
        return cls(
            label=prediction.label,
            confidence=prediction.confidence,
            segment_ids=prediction.segment_ids,
            segment_references=references,
            supporting_tokens=prediction.supporting_tokens,
            provider_context=prediction.provider_context,
            metadata=prediction.metadata,
            classifier_id=prediction.classifier_id
        )


class RootCauseAnalysisEngine:
    """Complete engine for root cause analysis with enhanced segment references."""
    
    # ... existing methods ...
    
    def analyze(self, segments: List["TokenizedSegment"]) -> List[RootCausePrediction]:
        """Analyze segments and return predictions with detailed segment references."""
        # Get raw predictions from classifiers
        raw_predictions = self.classifier_registry.classify(segments)
        
        # Handle fallback cases
        if self.enable_fallback and not raw_predictions:
            fallback_predictions = self.fallback_classifier.classify(segments)
            raw_predictions.extend(fallback_predictions)
            
        # Ensure last resort fallback if still no predictions
        if not raw_predictions:
            # ... create basic unclassified prediction ...
            
        # Coordinate predictions to resolve conflicts
            coordinated_predictions = self.coordinator.coordinate(raw_predictions)
        
        # Enrich predictions with metadata
        enriched_predictions = [
            self.coordinator.enrich_prediction_metadata(pred, segments)
            for pred in coordinated_predictions
        ]
        
        # Enhance with detailed segment references
        referenced_predictions = [
            RootCausePrediction.from_prediction(pred, segments)
            for pred in enriched_predictions
        ]
        
        return referenced_predictions
    
    def generate_summary_report(self, predictions: List[RootCausePrediction]) -> Dict[str, Any]:
        """Generate a summary report with detailed references to original logs."""
        if not predictions:
            return {"status": "no_issues_detected"}
            
        primary_issue = predictions[0]
        
        # Extract job contexts from predictions
        job_contexts = set()
        for pred in predictions:
            for ref in pred.segment_references:
                if ref.job_id:
                    job_contexts.add(ref.job_id)
        
        # Generate summary with traceability links
        summary = {
            "status": "issues_detected",
            "primary_issue": {
                "label": primary_issue.label,
                "confidence": primary_issue.confidence,
                "description": self._generate_issue_description(primary_issue),
                "evidence": primary_issue.supporting_tokens[:5]
            },
            "affected_jobs": list(job_contexts),
            "affected_sections": self._extract_affected_sections(predictions),
            "all_issues": [
                {
                    "label": p.label,
                    "confidence": p.confidence,
                    "references": [r.to_dict() for r in p.segment_references[:3]]  # Top 3 references
                }
                for p in predictions
            ],
            "trace_urls": self._extract_direct_links(predictions)
        }
        
        return summary
    
    def _generate_issue_description(self, prediction: RootCausePrediction) -> str:
        """Generate a human-readable description of the issue."""
        # Map of labels to human-readable descriptions
        descriptions = {
            "BUILD_FAILURE": "Build process failed during compilation",
            "TEST_FAILURE": "One or more tests failed during execution",
            "OUT_OF_MEMORY": "Process terminated due to memory exhaustion",
            "MISSING_DEPENDENCY": "Required dependency was not found",
            "PERMISSION_DENIED": "Process lacked required permissions",
            "TIMEOUT": "Operation exceeded the maximum allowed time",
            "CONFIGURATION_ERROR": "Incorrect or invalid configuration",
            # ... more descriptions ...
            "UNCLASSIFIED": "An issue was detected but could not be classified"
        }
        
        base_desc = descriptions.get(prediction.label, "An issue was detected in the CI process")
        
        # Enhance with specific details if available
        if prediction.supporting_tokens:
            token = prediction.supporting_tokens[0]
            if len(token) > 100:
                token = token[:97] + "..."
            base_desc += f": {token}"
            
        return base_desc
    
    def _extract_affected_sections(self, predictions: List[RootCausePrediction]) -> List[str]:
        """Extract unique affected sections from predictions."""
        sections = set()
        for pred in predictions:
            for ref in pred.segment_references:
                if ref.section:
                    sections.add(ref.section)
        
        return list(sections)
    
    def _extract_direct_links(self, predictions: List[RootCausePrediction]) -> List[Dict[str, Any]]:
        """Extract direct links to log sections for traceability."""
        links = []
        for pred in predictions:
            for ref in pred.segment_references:
                if ref.url:
                    link = {
                        "label": pred.label,
                        "url": ref.url,
                        "context": {
                            "job_id": ref.job_id,
                            "section": ref.section,
                            "line_range": ref.line_range
                        } if ref.job_id else {}
                    }
                    links.append(link)
        
        return links