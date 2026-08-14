from __future__ import annotations
import csv
import json
import sys
from collections.abc import Iterable, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, TextIO
from loadweave.contracts import Record

class CsvSource:
    def __init__(self, path: str, encoding: str = "utf-8", delimiter: str = ",") -> None:
        self.path, self.encoding, self.delimiter = Path(path), encoding, delimiter

    def read(self) -> Iterator[Record]:
        with self.path.open(encoding=self.encoding, newline="") as stream:
            yield from csv.DictReader(stream, delimiter=self.delimiter)

class JsonlSource:
    def __init__(self, path: str, encoding: str = "utf-8") -> None:
        self.path, self.encoding = Path(path), encoding

    def read(self) -> Iterator[Record]:
        with self.path.open(encoding=self.encoding) as stream:
            for number, line in enumerate(stream, 1):
                if line.strip():
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise ValueError(f"{self.path}:{number}: expected a JSON object")
                    yield value

class SelectFields:
    def __init__(self, fields: Sequence[str]) -> None:
        self.fields = tuple(fields)

    def apply(self, record: Record) -> Record:
        return {field: record.get(field) for field in self.fields}

class RenameFields:
    def __init__(self, fields: Mapping[str, str]) -> None:
        self.fields = dict(fields)

    def apply(self, record: Record) -> Record:
        return {self.fields.get(key, key): value for key, value in record.items()}

class DropEmpty:
    def __init__(self, field: str) -> None:
        self.field = field

    def apply(self, record: Record) -> Record | None:
        return record if record.get(self.field) not in (None, "") else None

class JsonlSink:
    def __init__(self, path: str, encoding: str = "utf-8") -> None:
        self.path, self.encoding = Path(path), encoding

    def write(self, records: Iterable[Record]) -> int:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with self.path.open("w", encoding=self.encoding) as stream:
            for record in records:
                stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
                count += 1
        return count

class StdoutSink:
    def __init__(self, stream: TextIO | None = None, **_: Any) -> None:
        self.stream = stream or sys.stdout

    def write(self, records: Iterable[Record]) -> int:
        count = 0
        for record in records:
            print(json.dumps(record, ensure_ascii=False), file=self.stream)
            count += 1
        return count

