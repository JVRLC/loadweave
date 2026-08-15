from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from time import monotonic

from loadweave.contracts import Record, Sink, Source, Transform


@dataclass(frozen=True)
class RunResult:
    extracted: int
    loaded: int
    elapsed_seconds: float


class Pipeline:
    def __init__(self, source: Source, transforms: Iterable[Transform], sink: Sink) -> None:
        self.source, self.transforms, self.sink = source, tuple(transforms), sink

    def run(self) -> RunResult:
        started, extracted = monotonic(), 0

        def records() -> Iterator[Record]:
            nonlocal extracted
            for record in self.source.read():
                extracted += 1
                current: Record | None = record
                for transform in self.transforms:
                    if current is None:
                        break
                    current = transform.apply(current)
                if current is not None:
                    yield current

        loaded = self.sink.write(records())
        return RunResult(extracted, loaded, monotonic() - started)
