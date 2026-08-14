from abc import ABC, abstractmethod
from typing import Iterator


class BasePCLoader(ABC):
    source_name: str
    source_type: str  # 'prestataire' | 'open_source' | 'interne'
    source_description: str = ""

    @abstractmethod
    def iter_items(self) -> Iterator[dict]: ...
