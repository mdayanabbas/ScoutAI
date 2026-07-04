from enum import StrEnum


class Environment(StrEnum):
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


SUPPORTED_ENVIRONMENTS: set[str] = {
    Environment.LOCAL,
    Environment.DEVELOPMENT,
    Environment.STAGING,
    Environment.PRODUCTION,
}

DEFAULT_API_PREFIX: str = "/api/v1"
DEFAULT_PAGINATION_LIMIT: int = 20
MAX_PAGINATION_LIMIT: int = 100
