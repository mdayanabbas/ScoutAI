from app.core.config import get_settings
from app.search.providers.base import WebSearchProvider
from app.search.providers.brave import BraveSearchProvider
from app.search.providers.tavily import TavilySearchProvider


def create_web_search_provider() -> WebSearchProvider:
    settings = get_settings()
    provider = (settings.WEB_SEARCH_PROVIDER or "tavily").strip().lower()
    if provider == "brave":
        return BraveSearchProvider()
    return TavilySearchProvider()
