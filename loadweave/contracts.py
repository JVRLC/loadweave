from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any, Protocol, runtime_checkable

Record = dict[str, Any]


@runtime_checkable
class Source(Protocol):
    def read(self) -> Iterator[Record]: ...


@runtime_checkable
class Transform(Protocol):
    def apply(self, record: Record) -> Record | None: ...


@runtime_checkable
class Sink(Protocol):
    def write(self, records: Iterable[Record]) -> int: ...
