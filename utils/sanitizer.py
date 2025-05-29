import re
from typing import Tuple, Dict, List

class LogSanitizer:
    def __init__(self, preserve_patterns: List[str] = None, **kwargs):
        self.preserve_patterns = preserve_patterns or []

    def sanitize(self, line: str) -> Tuple[str, Dict[str, str]]:
        metadata = {}
        preserved = []

        for pattern in self.preserve_patterns:
            matches = re.findall(pattern, line)
            preserved.extend(matches)

        # Remove everything that is not preserved
        sanitized = line
        for match in preserved:
            sanitized = sanitized.replace(match, '')

        sanitized = sanitized.strip()
        metadata['preserved'] = preserved
        return sanitized, metadata
