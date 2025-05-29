class BufferedStreamReader:
    def __init__(self, file_path, encoding="utf-8"):
        self.file_path = file_path
        self.encoding = encoding
        self._lines = []
        self._index = 0
        self._load_lines()

    def _load_lines(self):
        with open(self.file_path, "r", encoding=self.encoding) as f:
            self._lines = f.readlines()

    def __iter__(self):
        return iter(self._lines)

    def readline(self):
        if self._index < len(self._lines):
            line = self._lines[self._index]
            self._index += 1
            return line
        return ""

    def seek(self, index):
        self._index = index

    def tell(self):
        return self._index
