import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from tokenization.token_types import TokenType, TokenTypeSeverity, TokenSuppressionRule


# =============================================================================
# === Token and TokenizedSegment
# =============================================================================
@dataclass
class Token:
    type: TokenType
    value: str
    line_reference: int
    source_line: Any
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenizedSegment:
    segment_id: str
    tokens: List[Token]
    segment_type: str
    confidence: float
    context: Dict[str, Any]
    parent_segment_id: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None
    provider: Optional[str] = None
    related_segments: List[str] = field(default_factory=list)

    @property
    def raw_text(self) -> str:
        return "\n".join(token.value for token in self.tokens)

    @property
    def line_range(self) -> tuple:
        return (self.start_line or 0, self.end_line or 0)


@dataclass
class TokenRelationship:
    source_token: Token
    target_token: Token
    relationship_type: str
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# === Conflict Resolution Rules
# =============================================================================
class SpecializedConflictRules:
    """Specialized rules for common token classification conflicts."""

    @staticmethod
    def resolve_test_vs_general_error(message: str, context: Dict[str, Any]) -> TokenType:
        if context.get('in_test_context', False):
            return TokenType.TEST_FAILURE

        test_patterns = [
            r'assert.*failed', r'expected .* but got', r'should (?:be|have|contain)',
            r'expected:.*actual:', r'\d+ tests? failed', r'failure in test', r'test.*failed'
        ]
        if any(re.search(p, message, re.IGNORECASE) for p in test_patterns):
            return TokenType.TEST_FAILURE

        if context.get('in_stack_trace', False):
            return TokenType.ERROR

        return TokenType.ERROR

    @staticmethod
    def resolve_build_vs_general_error(message: str, context: Dict[str, Any]) -> TokenType:
        build_patterns = [
            r'compile[d]? error', r'build failed', r'cannot find symbol', r'syntax error',
            r'undefined reference to',
            r'error: [\w\d/\\]+\.(?:java|cpp|c|h|py|js|ts):\d+',
            r'could not resolve', r'failed to resolve'
        ]
        if any(re.search(p, message, re.IGNORECASE) for p in build_patterns):
            return TokenType.COMPILATION_ERROR

        if context.get('section') and 'build' in context.get('section').lower():
            return TokenType.COMPILATION_ERROR

        return TokenType.ERROR

    @staticmethod
    def resolve_provider_specific_annotations(message: str, provider: str) -> Optional[TokenType]:
        if provider == 'github_actions':
            if '##[error]' in message:
                return TokenType.CI_ERROR
            elif '##[warning]' in message:
                return TokenType.CI_WARNING

        elif provider == 'gitlab_ci':
            if re.match(r'ERROR: ', message):
                return TokenType.CI_ERROR

        return None


class GitHubActionsConflictRules:
    """GitHub Actions specific conflict resolution rules."""

    @staticmethod
    def apply_rules(token_types: List[TokenType], message: str, context: Dict[str, Any]) -> TokenType:
        if '##[' in message:
            for annotation_type in ['error', 'warning', 'notice', 'debug']:
                if f'##[{annotation_type}]' in message:
                    return {
                        'error': TokenType.CI_ERROR,
                        'warning': TokenType.CI_WARNING,
                        'notice': TokenType.CI_ANNOTATION,
                        'debug': TokenType.CI_ANNOTATION
                    }[annotation_type]

        step_name = context.get('step_name', '').lower()
        if 'test' in step_name:
            for t in token_types:
                if t.category.name == 'FAILURE' and 'TEST' in t.name:
                    return t
        if any(term in step_name for term in ['build', 'compile', 'webpack', 'gradle', 'maven']):
            for t in token_types:
                if 'BUILD' in t.name or 'COMPILATION' in t.name:
                    return t

        return max(token_types, key=lambda t: t.severity.level)


class GitLabCIConflictRules:
    """GitLab CI specific conflict resolution rules."""

    @staticmethod
    def apply_rules(token_types: List[TokenType], message: str, context: Dict[str, Any]) -> TokenType:
        if 'section_start:' in message:
            return TokenType.SECTION_START
        elif 'section_end:' in message:
            return TokenType.SECTION_END

        if message.startswith("ERROR: "):
            return TokenType.CI_ERROR

        section = context.get('section', '').lower()
        if 'test' in section:
            for t in token_types:
                if t.category.name == 'FAILURE' and 'TEST' in t.name:
                    return t
        if 'build' in section:
            for t in token_types:
                if 'BUILD' in t.name or 'COMPILATION' in t.name:
                    return t

        if re.search(r'(Job failed|Job succeeded|exited with) \(?code: (\d+)', message):
            return TokenType.EXIT_CODE_NON_ZERO

        return max(token_types, key=lambda t: t.severity.level)


# =============================================================================
# === False Positive Filters
# =============================================================================
@dataclass
class FalsePositiveFilter:
    rule_type: TokenSuppressionRule
    pattern: str
    applies_to: List[TokenType]
    confidence_adjustment: float
    provider_specific: Optional[str] = None


# From snippet 14 — filters used by suppressor pipeline
error_suppressors = [
    FalsePositiveFilter(
        rule_type=TokenSuppressionRule.CONTEXTUAL_PHRASE,
        pattern=r"(?:acceptable|expected|ignore|ignoring|intentional)\s+error",
        applies_to=[TokenType.ERROR],
        confidence_adjustment=-0.8
    ),
    FalsePositiveFilter(
        rule_type=TokenSuppressionRule.EXACT_PHRASE,
        pattern=r"error tolerance|error bound|error margin|error rate",
        applies_to=[TokenType.ERROR],
        confidence_adjustment=-0.9
    )
]
