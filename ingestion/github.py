"""GitHub Actions log ingestor implementation."""
from typing import Iterator, Dict, Any, Optional, List
import re
from ingestion.factory import register_ingestor
from ingestion.base import BaseLogIngestor
from core.models import LogLine
from utils.sanitizer import LogSanitizer
from utils.metadata_injector import MetadataRule

@register_ingestor('github', detection_patterns={
    'strong_indicators': [
        r'##\[group\]',
        r'##\[section\]',
        r'##\[command\]',
        r'Run .+?/.+?@.+'
    ],
    'weak_indicators': [
        r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z\s',
        r'github\.com',
        r'actions/checkout@'
    ]
})
class GitHubActionsIngestor(BaseLogIngestor):
    """Specialized ingestor for GitHub Actions CI logs."""

    def __init__(self, file_handle, **config):
        self.file_handle = file_handle
        self.config = config
        self.sanitizer = LogSanitizer(
            preserve_patterns=[r'##\[[^\]]+\]'],
            **config.get('sanitizer_options', {})
        )

    def stream_log(self) -> Iterator[LogLine]:
        """Process and stream GitHub Actions log lines."""
        current_step = None
        current_group = None

        for line_num, line in enumerate(self.file_handle, start=1):
            sanitized_line, sanitization_metadata = self.sanitizer.sanitize(line)
            log_line = self._parse_line(sanitized_line, line_num, current_step, current_group)
            log_line.sanitization_metadata = sanitization_metadata

            if '##[group]' in line:
                current_group = line.replace('##[group]', '').strip()
                log_line.section = current_group
            elif '##[endgroup]' in line:
                current_group = None

            step_match = re.search(r'##\[step\](.*)', line)
            if step_match:
                current_step = step_match.group(1).strip()
                log_line.step_name = current_step

            yield self.normalize(log_line)

    def _parse_line(self, line: str, line_num: int,
                    current_step: Optional[str] = None,
                    current_group: Optional[str] = None) -> LogLine:
        """Parse a GitHub Actions log line into a structured LogLine object."""
        return LogLine(
            line_number=line_num,
            raw_content=line,
            step_name=current_step,
            section=current_group,
        )

    def get_metadata_rules(self) -> List[MetadataRule]:
        """Provide GitHub-specific metadata rules."""
        return [
            MetadataRule(
                name="github_workflow",
                pattern=r"Workflow: ([^\n]+)",
                fields={"repository": "\\1"},
                priority=750
            ),
            MetadataRule(
                name="github_action_exec",
                pattern=r"Run (.+?/.+?)@",
                fields={"step_name": "\\1", "tags": ["action"]},
                priority=750
            ),
            MetadataRule(
                name="github_step",
                pattern=r"##\\[step\\](.*)",
                fields={"step_name": "\\1", "section": "\\1"},
                priority=750
            ),
            MetadataRule(
                name="github_stream_type_stdout",
                pattern=r"^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d+Z",
                fields={"stream_type": "stdout"},
                priority=600
            )
        ]
