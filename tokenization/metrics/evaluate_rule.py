from typing import Optional
from tokenization.models import TokenizedSegment
from core.models import RootCausePrediction  # Adjust path as needed

def evaluate_rule(self, rule, segments: list[TokenizedSegment], segment: TokenizedSegment) -> Optional[RootCausePrediction]:
    """
    Evaluate a contextual rule against a segment and return a prediction if confidence passes the threshold.
    
    Args:
        rule: ContextualRule containing the match condition and label
        segments: All tokenized segments
        segment: The segment to evaluate
    
    Returns:
        RootCausePrediction if confident match found, else None
    """
    # 1. Find context
    context_segments = rule.context_resolver(segments, segment)
    
    # 2. Match regex
    if hasattr(rule.condition, "pattern"):
        match_obj = rule.condition.pattern.search(segment.text)
    else:
        match_obj = None
    
    if not match_obj:
        return None

    # 3. Compute confidence
    confidence = self._calculate_confidence(
        segments=segments,
        segment=segment,
        context_segments=context_segments,
        rule_name=rule.name,
        pattern=rule.condition.pattern.pattern,
        match_obj=match_obj
    )
    
    # 4. Return prediction if above threshold
    if confidence >= self.confidence_threshold:
        return RootCausePrediction(
            label=rule.label,
            confidence=confidence,
            segment_id=segment.segment_id,
            context=[ctx.segment_id for ctx in context_segments],
            rule_name=rule.name
        )
    
    return None
