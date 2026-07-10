from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    url: str
    description: str | None = None
    rank: int | None = None
    source: str | None = None
    language: str | None = None
    age: str | None = None
    provider_score: float | None = None
    extra_snippets: tuple[str, ...] = ()


@dataclass(frozen=True)
class WebSearchResponse:
    provider: str
    query: str
    success: bool
    results: tuple[WebSearchResult, ...] = ()
    status_code: int | None = None
    reason: str | None = None


class WebSearchProvider(ABC):
    name: str

    @abstractmethod
    async def search(
        self,
        query: str,
        *,
        count: int = 10,
    ) -> WebSearchResponse:
        ...
