# ingestion/generic.py

from ingestion.base import BaseLogIngestor
from ingestion.buffered_ingestion import LogSanitizer
from core.models import LogLine

class GenericLogIngestor(BaseLogIngestor):
    """Fallback ingestor for unrecognized CI providers."""

    def __init__(self, file_handle, **config):
        self.file_handle = file_handle
        self.config = config

    def stream_log(self):
        for line_num, line in enumerate(self.file_handle, start=1):
            sanitized_line, sanitization_metadata = LogSanitizer.sanitize(line)
            log_line = self._parse_line(sanitized_line, line_num)
            log_line.sanitization_metadata = sanitization_metadata
            yield log_line

    def _parse_line(self, line, line_num):
        timestamp = self._extract_timestamp(line)
        log_level = self._extract_log_level(line)
        return LogLine(
    line_number=line_num,
    raw_content=line,
    timestamp=timestamp,
    level=log_level,
    message=self._extract_message(line, timestamp, log_level),
    source="generic"  # <-- Required field
)

    def normalize(self, line):
        """Basic normalization fallback when provider is unknown."""
        # You can choose minimal parsing or return raw line
        return LogLine(
            line_number=None,
            raw_content=line,
            timestamp=None,
            level="info",
            message=line.strip()
    )

    # Dummy implementations
    def _extract_timestamp(self, line): return None
    def _extract_log_level(self, line): return "info"
    def _extract_message(self, line, ts, lvl): return line
