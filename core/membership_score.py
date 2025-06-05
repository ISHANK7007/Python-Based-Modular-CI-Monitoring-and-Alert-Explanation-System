def compute_membership_score(
    content_similarity: float,
    temporal_correlation: float,
    context_similarity: float,
    feedback_alignment: float,
    prediction_confidence: float,
    membership_stability: float,
    attribution_clarity: float
) -> float:
    """
    Computes the adjusted membership score for a job in a cluster.

    Returns:
        A float score between 0 and 1 representing soft membership confidence.
    """
    # Base similarity score
    overall_score = (
        (content_similarity * 0.5) +
        (temporal_correlation * 0.3) +
        (context_similarity * 0.15) +
        (feedback_alignment * 0.05)
    )

    # Adjustment using classifier-based confidence signals
    adjustment_factor = (
        0.7 + (
            0.3 * (
                prediction_confidence +
                membership_stability +
                attribution_clarity
            ) / 3
        )
    )

    # Final score
    adjusted_score = overall_score * adjustment_factor
    return adjusted_score


# Example usage (for testing/demo):
if __name__ == "__main__":
    score = compute_membership_score(
        content_similarity=0.68,
        temporal_correlation=0.92,
        context_similarity=0.77,
        feedback_alignment=0.85,
        prediction_confidence=0.82,
        membership_stability=0.91,
        attribution_clarity=0.75
    )
    print(f"Adjusted membership score: {score:.4f}")
