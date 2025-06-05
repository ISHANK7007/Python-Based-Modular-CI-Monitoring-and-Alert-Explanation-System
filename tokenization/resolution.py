import re
from typing import List, Dict, Any
from tokenization.token_types import TokenType

class TokenConflictResolver:
    """Resolves conflicts when multiple token types are detected on a single line."""

    def __init__(self, provider: str = None):
        self.provider = provider
        self.severity_order = {
            TokenType.STACK_TRACE: 1,
            TokenType.TEST_ERROR: 2,
            TokenType.TEST_FAILURE: 3,
            TokenType.ERROR: 4,
            TokenType.CI_ERROR: 5,
            TokenType.ASSERTION_FAIL: 6,
            TokenType.EXIT_CODE_NON_ZERO: 7,
            TokenType.WARNING: 8,
            TokenType.INFO: 9,
            TokenType.DEFAULT: 99
        }

    def resolve_with_patterns(
        self, message: str, candidates: List[TokenType], context: Dict[str, Any]
    ) -> TokenType:
        """Resolve conflicts using severity and provider context."""

        if self.provider == 'github_actions':
            if '##[error]' in message:
                return TokenType.CI_ERROR
            if '##[warning]' in message:
                return TokenType.CI_WARNING

        if self.provider == 'gitlab_ci':
            if 'ERROR:' in message:
                return TokenType.CI_ERROR

        # Severity-based fallback
        sorted_candidates = sorted(
            candidates, key=lambda t: self.severity_order.get(t, 999)
        )
        return sorted_candidates[0]
