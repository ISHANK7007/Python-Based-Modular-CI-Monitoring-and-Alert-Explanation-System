import re
import datetime
import json
from typing import Iterator, Dict, Any, Match, Optional, List, Tuple
from collections import deque
from .factory import register_ingestor

from .base import BaseLogIngestor
from core.models import LogLine
from utils.section_validator import SectionValidator, ValidationLevel

@register_ingestor("gitlab", detection_patterns={
    "strong_indicators": [
        r'section_start:\d+:[^$]+$',
        r'section_end:\d+:[^$]+$',
        r'Running with gitlab-runner'
    ],
    "weak_indicators": [
        r'gitlab-ci\.yml',
        r'\$ gitlab-runner'
    ]
})
class GitLabCIIngestor(BaseLogIngestor):
    """Ingestor for GitLab CI/CD job logs with section validation."""

    SECTION_START_PATTERN = re.compile(r'^section_start:(\d+):([^\[\s]+)(?:\[(.*)\])?\r?$')
    SECTION_END_PATTERN = re.compile(r'^section_end:(\d+):([^\s]+)\r?$')
    STANDARD_LINE_PATTERN = re.compile(r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)?\s*(.*)$')
    JOB_INFO_PATTERN = re.compile(r'^(Running with gitlab-runner|Job succeeded|Job failed)')

    def __init__(self, file_handle_or_path: Any, **config):
        self.provider_id = "gitlab"
        super().__init__(file_handle_or_path, **config)
        self.section_stack = deque()
        self.section_metadata = {}
        self.section_validator = SectionValidator(auto_close_sections=config.get("auto_close_sections", True))
        self.include_validation_issues = config.get("include_validation_issues", True)

    def stream_log(self, source: str = None) -> Iterator[LogLine]:
        if hasattr(self.file_handle, "readlines"):
            raw_logs = self.file_handle.readlines()
        elif source and re.match(r'^\d+$', source):
            raw_logs = self._fetch_logs_from_gitlab_api(source)
        elif source and source.startswith(('http://', 'https://')):
            job_id = self._extract_job_id_from_url(source)
            raw_logs = self._fetch_logs_from_gitlab_api(job_id)
        elif source:
            with open(source, 'r', encoding='utf-8') as f:
                raw_logs = f.readlines()
        else:
            raise ValueError("Invalid source or file_handle for GitLabCIIngestor.")

        final_line_number = 0
        for line_num, raw_line in enumerate(raw_logs, start=1):
            final_line_number = line_num
            normalized = self._process_line(raw_line, line_num)
            if normalized:
                yield normalized

        for issue in self.section_validator.finalize(final_line_number):
            if self.include_validation_issues and issue.level != ValidationLevel.INFO:
                yield LogLine(
                    line_number=issue.line_number,
                    level="WARNING" if issue.level == ValidationLevel.WARNING else "ERROR",
                    message=f"[Section Validation] {issue.message}",
                    provider="gitlab",
                    section=issue.section_name,
                    tags=["section_validation", issue.level.value],
                    provider_metadata={"validation_issue": issue.context}
                )

    def _process_line(self, raw_line: str, line_num: int) -> Optional[LogLine]:
        original = raw_line.rstrip()
        cleaned = original

        start_match = self.SECTION_START_PATTERN.match(cleaned)
        if start_match:
            return self._process_section_start(start_match, original, line_num)

        end_match = self.SECTION_END_PATTERN.match(cleaned)
        if end_match:
            return self._process_section_end(end_match, original, line_num)

        return self._process_standard_line(cleaned, original, line_num)

    def _process_section_start(self, match: Match, original: str, line_num: int) -> LogLine:
        timestamp_unix = float(match.group(1))
        section_name = match.group(2)
        args_str = match.group(3) or ""
        collapsed = "collapsed=true" in args_str

        timestamp = datetime.datetime.fromtimestamp(timestamp_unix, tz=datetime.timezone.utc)
        self.section_validator.start_section(section_name, line_num, timestamp_unix, collapsed)

        self.section_stack.append((section_name, [section_name]))  # Simplified path tracking
        return LogLine(
            line_number=line_num,
            timestamp=timestamp,
            level="info",
            message=f"Section started: {section_name}",
            provider="gitlab",
            section=section_name,
            provider_metadata={"section_args": args_str, "collapsed": collapsed},
            raw_content=original
        )

    def _process_section_end(self, match: Match, original: str, line_num: int) -> LogLine:
        timestamp_unix = float(match.group(1))
        section_name = match.group(2)
        timestamp = datetime.datetime.fromtimestamp(timestamp_unix, tz=datetime.timezone.utc)

        section = self.section_validator.end_section(section_name, line_num, timestamp_unix)
        if section and self.section_stack and self.section_stack[-1][0] == section_name:
            self.section_stack.pop()

        return LogLine(
            line_number=line_num,
            timestamp=timestamp,
            level="info",
            message=f"Section ended: {section_name}",
            provider="gitlab",
            section=section_name,
            provider_metadata={"complete": True, "duration": section.duration if section else None},
            raw_content=original
        )

    def _process_standard_line(self, cleaned_line: str, original: str, line_num: int) -> LogLine:
        std_match = self.STANDARD_LINE_PATTERN.match(cleaned_line)
        timestamp_str = std_match.group(1) if std_match else None
        message = std_match.group(2) if std_match else cleaned_line

        timestamp = (datetime.datetime.strptime(timestamp_str, '%Y-%m-%dT%H:%M:%S.%f')
                     .replace(tzinfo=datetime.timezone.utc)) if timestamp_str else datetime.datetime.now(datetime.timezone.utc)

        level = "info"
        if re.search(r'(error|fatal|failed)', message, re.IGNORECASE):
            level = "error"
        elif re.search(r'warning', message, re.IGNORECASE):
            level = "warning"
        elif self.JOB_INFO_PATTERN.match(message):
            level = "info"

        section_context = self.section_validator.get_section_at_line(line_num)
        innermost = section_context[-1].name if section_context else None
        section_path = [s.name for s in section_context] if section_context else []

        return LogLine(
            line_number=line_num,
            timestamp=timestamp,
            level=level,
            message=message,
            provider="gitlab",
            section=innermost,
            provider_metadata={
                "section_path": section_path,
                "has_explicit_timestamp": bool(timestamp_str)
            },
            raw_content=original
        )

    def _fetch_logs_from_gitlab_api(self, job_id: str) -> List[str]:
        return [  # Placeholder stub for now
            f"section_start:1716816585:setup[collapsed=true]",
            f"2023-06-15T14:23:41.123Z Initializing environment",
            f"2023-06-15T14:23:42.456Z Step 1 complete",
            f"section_end:1716816600:setup",
        ]

    def _extract_job_id_from_url(self, url: str) -> str:
        match = re.search(r'/jobs/(\d+)', url)
        return match.group(1) if match else ""

    def get_section_structure(self) -> List[Dict[str, Any]]:
        return self.section_validator.get_section_hierarchy()

    def filter_by_section(self, section_name: str, log_iterator: Iterator[LogLine]) -> Iterator[LogLine]:
        return (line for line in log_iterator if line.section == section_name)

    def filter_by_section_path(self, section_path: List[str], log_iterator: Iterator[LogLine]) -> Iterator[LogLine]:
        path_str = json.dumps(section_path)
        return (line for line in log_iterator if json.dumps(line.provider_metadata.get("section_path", [])) == path_str)
