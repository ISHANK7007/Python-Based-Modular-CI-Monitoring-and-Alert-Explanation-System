from typing import List, Dict, Any
from tokenization.segment_rules import ClassificationRule
from tokenization.token_relationship import TokenizedSegment

class SegmentClassifier:
    """Classifies TokenizedSegments into semantic categories."""
    
    def __init__(self, classification_rules: List[ClassificationRule], config: Dict[str, Any] = None):
        self.rules = classification_rules
        self.config = config or {}

    def classify(self, segment: TokenizedSegment) -> TokenizedSegment:
        """Apply classification rules to determine segment type and properties."""
        for rule in self.rules:
            if rule.matches(segment):
                segment.context['classification'] = rule.classification_type
                segment.context['confidence'] = rule.calculate_confidence(segment)
                segment.context.update(rule.extract_metadata(segment))
        return segment
