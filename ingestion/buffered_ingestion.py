# ingestion/buffered_ingestion.py

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
# ingestion/buffered_ingestion.py

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
