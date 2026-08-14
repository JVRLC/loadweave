from __future__ import annotations
from collections.abc import Iterable, Iterator
from typing import Any, Protocol

Record = dict[str, Any]

class Source(Protocol):
    def read(self) -> Iterator[Record]: ...

class Transform(Protocol):
    def apply(self, record: Record) -> Record | None: ...

class Sink(Protocol):
    def write(self, records: Iterable[Record]) -> int: ...

