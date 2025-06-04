from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from core.segment_reference import SegmentReference  # Adjust import path if needed

@dataclass
class ExplanationBundle:
    """Comprehensive bundle of explanation data and metadata"""
    
    # Core explanation content
    summary_text: str  # Brief, headline-style summary
    detailed_text: str  # Full explanation in the target format

    # Metadata
    prediction_id: str  # Reference to the source prediction
    label: str  # The identified root cause label
    confidence_level: float  # 0.0–1.0 scale
    confidence_category: str  # "high", "medium", "low"

    # Rendering information
    format: str  # "markdown", "json", "plaintext", etc.
    render_style: str  # Renderer-specific style information
    verbosity_level: int  # 0=minimal, 1=standard, 2=verbose, 3=diagnostic

    # Evidence information
    segments_used: List[SegmentReference]  # Segments used in explanation
    supporting_tokens: List[str]  # Key evidence tokens

    # Traceability
    job_context: Optional[Dict[str, Any]]  # Job metadata if available
    generation_timestamp: str  # ISO format timestamp

    # Debugging/auditing
    render_trace_id: Optional[str]  # ID of render trace if available
    renderer_version: str  # Version of renderer used
    template_id: str  # Template identifier
    template_version: str  # Template version used

    # UI/UX helpers
    suggested_actions: List[Dict[str, str]]  # Recommended next steps
    related_documentation: List[Dict[str, str]]  # Links to helpful docs
    interactive_elements: Dict[str, Any]  # UI-specific interaction data
