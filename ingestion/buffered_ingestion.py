# ingestion/buffered_ingestion.py

from ingestion.base import BaseLogIngestor
from core.models import LogLine
from utils.buffered_stream_reader import BufferedStreamReader


class LogSanitizer:
    @staticmethod
    def sanitize(line: str):
        """Basic line sanitizer that strips whitespace."""
        cleaned_line = line.strip()
        metadata = {
            "original_length": len(line),
            "cleaned_length": len(cleaned_line),
            "was_trimmed": cleaned_line != line
        }
        return cleaned_line, metadata


class BufferedStreamReader:
    """Buffered wrapper that makes file path behave like file object with readlines()."""

    def __init__(self, file_path, buffer_size=8192):
        self.file_path = file_path
        self.buffer_size = buffer_size
        self._file = open(file_path, "r", encoding="utf-8")

    def __iter__(self):
        return self

    def __next__(self):
        line = self._file.readline()
        if not line:
            self._file.close()
            raise StopIteration
        return line

    def read(self, size=-1):
        return self._file.read(size)

    def tell(self):
        return self._file.tell()

    def seek(self, offset, whence=0):
        return self._file.seek(offset, whence)

    def close(self):
        self._file.close()


class BufferedLogIngestor(BaseLogIngestor):
    """Log ingestor that reads logs from a buffered file stream."""

    def stream_log(self, path: str):
        with BufferedStreamReader(path) as reader:
            for line in reader:
                yield self.parse_log_line(line)
