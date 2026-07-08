from abc import ABC, abstractmethod

from app.schemas.discovery import RawStartupCandidate
from app.utils.enums import DiscoverySource


class StartupSourceAdapter(ABC):
    source: DiscoverySource

    @abstractmethod
    async def discover(self, request: object | None = None) -> list[RawStartupCandidate]:
        """Return raw startup candidates without writing to persistence."""
