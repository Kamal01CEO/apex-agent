"""Base class for source document ingesters."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Union
from apex_agent.models import MemoryEvent


class BaseIngester(ABC):
    """Abstract ingester normalizing diverse files into MemoryEvents."""

    @abstractmethod
    def can_ingest(self, file_path: Union[str, Path]) -> bool:
        """Returns true if this ingester handles the given file."""
        pass

    @abstractmethod
    def ingest(self, file_path: Union[str, Path]) -> List[MemoryEvent]:
        """Parses the input file into one or more standardized MemoryEvents."""
        pass
