import io
import gzip
import bz2
import lzma
from typing import Iterator, TextIO, BinaryIO, Optional, Union, List, Callable, TypeVar
import requests
from urllib.parse import urlparse
import os
from contextlib import contextmanager
from abc import ABC, abstractmethod
from core.models import LogLine
from utils.metadata_injector import MetadataInjector, MetadataRule
from functools import wraps
from typing import Callable, Iterator
T = TypeVar('T')


class BufferedStreamReader:
    COMPRESSION_SIGNATURES = {
        b'\x1f\x8b': 'gzip',
        b'BZ': 'bzip2',
        b'\xFD\x37\x7A': 'lzma',
    }

    def __init__(self, source: Union[str, TextIO, BinaryIO, List[str]],
                 buffer_size: int = 8192,
                 encoding: str = 'utf-8',
                 auth: Optional[tuple] = None):
        self.source = source
        self.buffer_size = buffer_size
        self.encoding = encoding
        self.auth = auth
        self._file = None
        self._close_file = False

    def __enter__(self):
        self._file = self._open_source()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _open_source(self) -> TextIO:
        if isinstance(self.source, list):
            return io.StringIO('\n'.join(self.source))
        elif isinstance(self.source, str):
            if urlparse(self.source).scheme in ('http', 'https'):
                return self._open_url(self.source)
            else:
                return self._open_file_path(self.source)
        elif hasattr(self.source, 'read'):
            if hasattr(self.source, 'encoding'):
                return self.source
            else:
                return self._wrap_binary_stream(self.source)
        else:
            raise ValueError(f"Unsupported source type: {type(self.source)}")

    def _open_file_path(self, path: str) -> TextIO:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")

        if path.endswith('.gz'):
            self._close_file = True
            return io.TextIOWrapper(gzip.open(path, 'rb'), encoding=self.encoding)
        elif path.endswith('.bz2'):
            self._close_file = True
            return io.TextIOWrapper(bz2.open(path, 'rb'), encoding=self.encoding)
        elif path.endswith(('.xz', '.lzma')):
            self._close_file = True
            return io.TextIOWrapper(lzma.open(path, 'rb'), encoding=self.encoding)
        else:
            with open(path, 'rb') as f:
                magic_bytes = f.read(4)
                f.seek(0)
                for signature, format_name in self.COMPRESSION_SIGNATURES.items():
                    if magic_bytes.startswith(signature):
                        if format_name == 'gzip':
                            return io.TextIOWrapper(gzip.open(path, 'rb'), encoding=self.encoding)
                        elif format_name == 'bzip2':
                            return io.TextIOWrapper(bz2.open(path, 'rb'), encoding=self.encoding)
                        elif format_name == 'lzma':
                            return io.TextIOWrapper(lzma.open(path, 'rb'), encoding=self.encoding)

            return open(path, 'r', encoding=self.encoding, buffering=self.buffer_size)

    def _open_url(self, url: str) -> TextIO:
        response = requests.get(url, stream=True, auth=self.auth)
        response.raise_for_status()

        content_type = response.headers.get('Content-Type', '')
        content_encoding = response.headers.get('Content-Encoding', '')

        if 'gzip' in content_encoding or 'application/gzip' in content_type:
            stream = gzip.GzipFile(fileobj=response.raw)
        elif 'bzip2' in content_encoding or 'application/x-bzip2' in content_type:
            stream = bz2.BZ2File(response.raw)
        elif 'xz' in content_encoding or 'application/x-xz' in content_type:
            stream = lzma.LZMAFile(response.raw)
        else:
            peek = response.raw.peek(4)
            for signature, format_name in self.COMPRESSION_SIGNATURES.items():
                if peek.startswith(signature):
                    if format_name == 'gzip':
                        stream = gzip.GzipFile(fileobj=response.raw)
                        break
                    elif format_name == 'bzip2':
                        stream = bz2.BZ2File(response.raw)
                        break
                    elif format_name == 'lzma':
                        stream = lzma.LZMAFile(response.raw)
                        break
            else:
                stream = response.raw

        self._close_file = True
        return io.TextIOWrapper(stream, encoding=self.encoding)

    def _wrap_binary_stream(self, stream: BinaryIO) -> TextIO:
        if hasattr(stream, 'peek'):
            peek = stream.peek(4)
            for signature, format_name in self.COMPRESSION_SIGNATURES.items():
                if peek.startswith(signature):
                    if format_name == 'gzip':
                        return io.TextIOWrapper(gzip.GzipFile(fileobj=stream), encoding=self.encoding)
                    elif format_name == 'bzip2':
                        return io.TextIOWrapper(bz2.BZ2File(fileobj=stream), encoding=self.encoding)
                    elif format_name == 'lzma':
                        return io.TextIOWrapper(lzma.LZMAFile(fileobj=stream), encoding=self.encoding)
        return io.TextIOWrapper(stream, encoding=self.encoding)

    def readlines(self) -> Iterator[str]:
        if self._file is None:
            self._file = self._open_source()
            self._close_file = True

        for line in self._file:
            yield line.rstrip('\r\n')

    def close(self):
        if self._close_file and self._file:
            self._file.close()
            self._file = None
            self._close_file = False

    
def pipeline_processor(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(self, lines: Iterator[tuple[int, str]]) -> Iterator[tuple[int, str]]:
        return func(self, lines)
    return wrapper


class LogPipeline:
    def __init__(self, source: Union[str, TextIO, BinaryIO, List[str]],
                 buffer_size: int = 8192,
                 encoding: str = 'utf-8',
                 auth: Optional[tuple] = None):
        self.reader = BufferedStreamReader(source, buffer_size, encoding, auth)
        self.processors = []

    def add_processor(self, processor: Callable[[Iterator[T]], Iterator[T]]) -> 'LogPipeline':
        self.processors.append(processor)
        return self

    def process(self) -> Iterator[T]:
        with self.reader as reader:
            result = reader.readlines()
            for processor in self.processors:
                result = processor(result)
            yield from result


class BaseLogIngestor(ABC):
    def __init__(self, source_identifier: str = "", file_handle=None, **config):
        self.source_identifier = source_identifier
        self.file_handle = file_handle
        self.config = config

        file_path = getattr(file_handle, 'name', None) if file_handle else None
        self.metadata_injector = MetadataInjector(
            file_path=file_path,
            provider=getattr(self.__class__, 'provider_id', None),
            rules=self.get_metadata_rules()
        )

    def stream_log(self, source: Union[str, TextIO, BinaryIO, List[str]]) -> Iterator[LogLine]:
        pipeline = LogPipeline(source)
        pipeline.add_processor(self._track_line_numbers)
        for processor in self._get_preprocessors():
            pipeline.add_processor(processor)
        pipeline.add_processor(self._normalize_lines)
        return pipeline.process()

    @pipeline_processor
    def _track_line_numbers(self, lines: Iterator[str]) -> Iterator[tuple[int, str]]:
        for i, line in enumerate(lines, 1):
            yield (i, line)

    @pipeline_processor
    def _normalize_lines(self, lines: Iterator[tuple[int, str]]) -> Iterator[LogLine]:
        for line_number, line in lines:
            raw_line = LogLine(line_number=line_number, raw_content=line)
            normalized = self.normalize(raw_line)
            yield normalized

    def _get_preprocessors(self) -> List[Callable]:
        return []

    def normalize(self, log_line: LogLine) -> LogLine:
        normalized = self._provider_normalize(log_line)
        return self.metadata_injector.inject(normalized)

    def _provider_normalize(self, log_line: LogLine) -> LogLine:
        return log_line

    def get_metadata_rules(self) -> List[MetadataRule]:
        return []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        pass
    def process(self, lines: Iterator[tuple[int, str]]) -> Iterator[LogLine]:
        """Applies the preprocessing pipeline to raw lines and normalizes them into LogLine objects."""
        result = lines
        for processor in self._get_preprocessors():
            result = processor(result)
        return (self.normalize(line) for _, line in result)
    