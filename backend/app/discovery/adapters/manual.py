from app.discovery.adapters.base import StartupSourceAdapter
from app.schemas.discovery import ManualDiscoveryRequest, RawStartupCandidate
from app.utils.enums import DiscoverySource


class ManualDiscoveryAdapter(StartupSourceAdapter):
    source = DiscoverySource.MANUAL

    async def discover(self, request: object | None = None) -> list[RawStartupCandidate]:
        if not isinstance(request, ManualDiscoveryRequest):
            raise ValueError("ManualDiscoveryAdapter requires ManualDiscoveryRequest")
        return list(request.candidates)
