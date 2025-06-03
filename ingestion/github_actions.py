import re
import datetime
from typing import Iterator, Dict, Any, Match, Optional, Callable, List
from urllib.parse import urlparse

from .base import BaseLogIngestor, pipeline_processor
from core.models import LogLine

# Safe import for ANSI stripping
try:
    from ansiscape.stripping import strip as strip_ansi
except ImportError:
    def strip_ansi(text: str) -> str:
        return text  # Fallback no-op if library missing

class GitHubActionsIngestor(BaseLogIngestor):
    """Ingestor for GitHub Actions workflow logs with preprocessing pipeline."""

    TIMESTAMP_PATTERN = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+Z\s+'
    LOG_LEVEL_PATTERN = r'(debug|info|notice|warning|error|fatal)'

    STANDARD_LINE_PATTERN = re.compile(
        r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}.\d+Z)\s+' +
        r'(?:\[({})\])?\s*(.*)$'.format(LOG_LEVEL_PATTERN),
        re.IGNORECASE
    )

    STEP_START_PATTERN = re.compile(r'##\[group\](.*)')
    STEP_END_PATTERN = re.compile(r'##\[endgroup\]')

    ANNOTATION_PATTERN = re.compile(
        r'##\[(warning|error)\](.*?)' +
        r'(file=(.+?),line=(\d+),endLine=(\d+),col=(\d+),endColumn=(\d+))?'
    )

    def __init__(self, github_token: Optional[str] = None):
        super().__init__("github-actions")
        self.github_token = github_token
        self.current_step = None

    def _get_preprocessors(self) -> List[Callable]:
        """Add GitHub-specific line preprocessors."""
        return [
            self._preprocess_ansi_codes,
            self._track_step_context
        ]

    @pipeline_processor
    def _preprocess_ansi_codes(self, lines: Iterator[tuple[int, str]]) -> Iterator[tuple[int, str]]:
        for line_number, line in lines:
            cleaned = strip_ansi(line)
            yield (line_number, cleaned)

    @pipeline_processor
    def _track_step_context(self, lines: Iterator[tuple[int, str]]) -> Iterator[tuple[int, str]]:
        for line_number, line in lines:
            step_start_match = self.STEP_START_PATTERN.match(line)
            if step_start_match:
                self.current_step = step_start_match.group(1).strip()
            elif self.STEP_END_PATTERN.match(line):
                self.current_step = None
            yield (line_number, line)

    def normalize(self, raw_log_line: str) -> LogLine:
        original_line = raw_log_line
        cleaned_line = raw_log_line.strip()

        annotation_match = self.ANNOTATION_PATTERN.match(cleaned_line)
        if annotation_match:
            return self._process_annotation(annotation_match, original_line)

        std_match = self.STANDARD_LINE_PATTERN.match(cleaned_line)
        if std_match:
            return self._process_standard_line(std_match, original_line)

        return self._process_fallback_line(cleaned_line, original_line)

    def _process_annotation(self, match: Match, original: str) -> LogLine:
        level = match.group(1)
        message = match.group(2).strip()
        metadata = {'type': 'annotation', 'step': self.current_step}

        if match.group(3):
            metadata.update({
                'file': match.group(4),
                'line_start': int(match.group(5)),
                'line_end': int(match.group(6)),
                'col_start': int(match.group(7)),
                'col_end': int(match.group(8))
            })

        return LogLine(
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            level=level,
            message=message,
            source=self.source_identifier,
            metadata=metadata,
            raw_content=original
        )

    def _process_standard_line(self, match: Match, original: str) -> LogLine:
        timestamp_str = match.group(1)
        level = (match.group(2) or 'info').lower()
        message = match.group(3) or ""

        if '.' in timestamp_str:
            parts = timestamp_str.split('.')
            if len(parts[1]) > 6:
                microsecond = parts[1][:6]
                timestamp_str = f"{parts[0]}.{microsecond}Z"

        timestamp = datetime.datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)

        is_stderr = level in ('error', 'fatal', 'warning') or bool(
            re.search(r'(error|exception|fail|traceback)', message, re.IGNORECASE)
        )

        return LogLine(
            timestamp=timestamp,
            level=level,
            message=message,
            source=self.source_identifier,
            metadata={
                'step': self.current_step,
                'stream': 'stderr' if is_stderr else 'stdout',
                'type': 'log'
            },
            raw_content=original
        )

    def _process_fallback_line(self, cleaned_line: str, original: str) -> LogLine:
        is_stderr = bool(re.search(r'(error|exception|fail|traceback)', cleaned_line, re.IGNORECASE))

        return LogLine(
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            level='info',
            message=cleaned_line,
            source=self.source_identifier,
            metadata={
                'step': self.current_step,
                'stream': 'stderr' if is_stderr else 'stdout',
                'type': 'command_output'
            },
            raw_content=original
        )

    def filter_by_step(self, step_name: str, log_iterator: Iterator[LogLine]) -> Iterator[LogLine]:
        return (line for line in log_iterator if line.metadata.get('step') == step_name)

    def filter_errors_and_warnings(self, log_iterator: Iterator[LogLine]) -> Iterator[LogLine]:
        return (line for line in log_iterator if
                line.level in ('error', 'fatal', 'warning') or
                line.metadata.get('type') == 'annotation')

    def stream_log(self, source: str) -> Iterator[LogLine]:
        """Reads the log file and yields normalized LogLine objects."""
        with open(source, "r", encoding="utf-8") as file:
            lines = ((i, line.rstrip("\n")) for i, line in enumerate(file))
            for processed in self.process(lines):
                yield processed
