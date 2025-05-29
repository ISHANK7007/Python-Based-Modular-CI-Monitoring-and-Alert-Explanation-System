from typing import List
from tokenization.models import TokenizedSegment, Token
from tokenization.token_types import TokenType, TokenCategory  # Optional if context logic needs type-specific heuristics

class ContextAwareClassifier:
    """Refines token classifications based on segment-level context."""

    def refine_classifications(
        self,
        segment: TokenizedSegment,
        surrounding_segments: List[TokenizedSegment]
    ) -> TokenizedSegment:
        """
        Refine token classifications using information from surrounding segments.

        This can help disambiguate token roles or promote generic tokens to specific types.
        """
        # Example heuristic: elevate DEFAULT tokens if neighboring segments show consistent failure pattern
        failure_context = any(seg.contains_failure for seg in surrounding_segments)

        for token in segment.tokens:
            if token.type == TokenType.DEFAULT and failure_context:
                # Hypothetically elevate based on context (you can make this smarter)
                token.type = TokenType.ERROR  # placeholder assumption
                token.metadata["context_promoted"] = True

        return segment
