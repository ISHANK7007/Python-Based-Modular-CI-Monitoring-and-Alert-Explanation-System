import re
import collections
from abc import ABC, abstractmethod
from typing import Iterator, List, Dict, Any, Optional
from tokenization.models import TokenizedSegment, Token
from tokenization.token_types import TokenType, TokenCategory
from core.models import LogLine
from tokenization.resolution import TokenConflictResolver
from tokenization.registry import register_classifier


class ContextAwareClassifier:
    """Refines token classifications based on segment-level context."""
    def analyze(self, segments: List[TokenizedSegment]) -> List[TokenizedSegment]:
        # Dummy logic for now; extend with actual context analysis
        for segment in segments:
            segment.context = {"contextual_tag": "default"}  # Replace with real logic
        return segments
    def refine_classifications(
        self,
        segment: TokenizedSegment,
        surrounding_segments: List[TokenizedSegment]
    ) -> TokenizedSegment:
        """
        Refine token classifications using information from surrounding segments.
        This can help disambiguate token roles or promote generic tokens to specific types.
        """
        failure_context = any(seg.contains_failure for seg in surrounding_segments)

        for token in segment.tokens:
            if token.type == TokenType.DEFAULT and failure_context:
                token.type = TokenType.ERROR  # placeholder assumption
                token.metadata["context_promoted"] = True

        return segment


class BaseTokenClassifier(ABC):
    """Responsible for classifying individual log lines into tokens."""

    def __init__(self, provider: str = None):
        self.provider = provider

    @abstractmethod
    def classify_line(self, log_line: LogLine) -> Token:
        pass

    def process_stream(self, log_lines: Iterator[LogLine]) -> Iterator[Token]:
        for line in log_lines:
            yield self.classify_line(line)


@register_classifier('github_actions')
class GitHubActionsClassifier(BaseTokenClassifier):
    """GitHub Actions-specific token classifier."""

    def classify_line(self, log_line: LogLine) -> Token:
        message = log_line.message

        if '##[' in message:
            match = re.search(r'##\[(warning|error|notice|debug|group|endgroup)\]', message)
            if match:
                annotation_type = match.group(1)
                return Token(
                    type=self._map_annotation_to_token_type(annotation_type),
                    value=message,
                    line_reference=log_line.line_number,
                    source_line=log_line,
                    metadata={'annotation_type': annotation_type}
                )

        for token_type in TokenType:
            for pattern in token_type.typical_patterns:
                if pattern and pattern in message:
                    return Token(
                        type=token_type,
                        value=message,
                        line_reference=log_line.line_number,
                        source_line=log_line
                    )

        if log_line.level:
            level_map = {
                'error': TokenType.ERROR,
                'warning': TokenType.WARNING,
                'info': TokenType.INFO,
                'debug': TokenType.DEBUG,
                'trace': TokenType.TRACE,
                'verbose': TokenType.VERBOSE
            }
            if log_line.level.lower() in level_map:
                return Token(
                    type=level_map[log_line.level.lower()],
                    value=message,
                    line_reference=log_line.line_number,
                    source_line=log_line
                )

        return Token(
            type=TokenType.DEFAULT,
            value=message,
            line_reference=log_line.line_number,
            source_line=log_line
        )


class EnhancedTokenClassifier(BaseTokenClassifier):
    """Token classifier with conflict resolution capabilities."""

    def __init__(self, provider: str = None):
        super().__init__(provider)
        self.conflict_resolver = TokenConflictResolver(provider)
        self.context = {
            'recent_token_types': collections.deque(maxlen=5),
            'in_test_context': False,
            'in_stack_trace': False,
            'section': None
        }

    def classify_line(self, log_line: LogLine) -> Token:
        self._update_context_from_line(log_line)
        candidate_types = self._identify_candidate_types(log_line)

        if len(candidate_types) > 1:
            resolved_type = self.conflict_resolver.resolve_with_patterns(
                log_line.message, candidate_types, self.context)
        elif candidate_types:
            resolved_type = candidate_types[0]
        else:
            resolved_type = TokenType.DEFAULT

        self.context['recent_token_types'].appendleft(resolved_type)

        return Token(
            type=resolved_type,
            value=log_line.message,
            line_reference=log_line.line_number,
            source_line=log_line,
            metadata=self._extract_metadata(log_line, resolved_type)
        )

    def _update_context_from_line(self, log_line: LogLine):
        if log_line.section:
            self.context['section'] = log_line.section
            self.context['in_test_context'] = (
                'test' in log_line.section.lower() or
                (log_line.step_name and 'test' in log_line.step_name.lower())
            )
        if any(p in log_line.message for p in [
            'Traceback', 'at ', 'caused by', 'Exception in thread'
        ]):
            self.context['in_stack_trace'] = True
        elif not log_line.message.startswith((' ', '\t')):
            self.context['in_stack_trace'] = False

    def _identify_candidate_types(self, log_line: LogLine) -> List[TokenType]:
        message = log_line.message.lower()
        candidates = []

        provider_candidates = self._provider_specific_candidates(log_line)
        candidates.extend(provider_candidates)

        for token_type in TokenType:
            if token_type in candidates:
                continue
            for pattern in token_type.typical_patterns or []:
                if pattern and pattern.lower() in message:
                    candidates.append(token_type)
                    break

        if not candidates and log_line.level:
            level_map = {
                'error': TokenType.ERROR,
                'warning': TokenType.WARNING,
                'info': TokenType.INFO,
                'debug': TokenType.DEBUG,
                'trace': TokenType.TRACE,
                'verbose': TokenType.VERBOSE
            }
            level = log_line.level.lower()
            if level in level_map:
                candidates.append(level_map[level])

        if self.context.get('in_test_context'):
            if 'fail' in message or 'failed' in message:
                candidates.append(TokenType.TEST_FAILURE)
            elif 'error' in message:
                candidates.append(TokenType.TEST_ERROR)

        if self.context.get('in_stack_trace'):
            candidates.append(TokenType.STACK_TRACE)

        if not candidates:
            candidates.append(TokenType.DEFAULT)

        return candidates

    def _provider_specific_candidates(self, log_line: LogLine) -> List[TokenType]:
        message = log_line.message
        candidates = []

        if self.provider == 'github_actions':
            if '##[' in message:
                match = re.search(r'##\[(warning|error|notice|debug|group|endgroup)\]', message)
                if match:
                    annotation_type = match.group(1)
                    candidates.append({
                        'warning': TokenType.CI_WARNING,
                        'error': TokenType.CI_ERROR,
                        'group': TokenType.SECTION_START,
                        'endgroup': TokenType.SECTION_END
                    }.get(annotation_type, TokenType.CI_ANNOTATION))

        elif self.provider == 'gitlab_ci':
            if 'section_start:' in message:
                candidates.append(TokenType.SECTION_START)
            elif 'section_end:' in message:
                candidates.append(TokenType.SECTION_END)
            if 'ERROR: ' in message:
                candidates.append(TokenType.CI_ERROR)

        return candidates

    def _extract_metadata(self, log_line: LogLine, token_type: TokenType) -> Dict[str, Any]:
        metadata = {}
        message = log_line.message

        if log_line.timestamp:
            metadata['timestamp'] = log_line.timestamp

        if token_type == TokenType.EXIT_CODE_NON_ZERO:
            match = re.search(r'exit(?:ed)? (?:with )?code[:]? (\d+)', message.lower())
            if match:
                metadata['exit_code'] = int(match.group(1))

        elif token_type == TokenType.TEST_FAILURE:
            match = re.search(r'test[\s_]([a-zA-Z0-9_]+)', message, re.IGNORECASE)
            if match:
                metadata['test_name'] = match.group(1)
            if 'expected' in message.lower() and 'actual' in message.lower():
                metadata['has_expectation_mismatch'] = True

        elif token_type == TokenType.STACK_TRACE:
            if 'Traceback' in message:
                metadata['language'] = 'python'
            elif 'at ' in message and ('.java:' in message or '.kt:' in message):
                metadata['language'] = 'java'
            elif 'at ' in message and '.js:' in message:
                metadata['language'] = 'javascript'
            file_match = re.search(r'(?:at |File ")([^:]+):(\d+)', message)
            if file_match:
                metadata['file'] = file_match.group(1)
                metadata['line_number'] = int(file_match.group(2))

        return metadata
