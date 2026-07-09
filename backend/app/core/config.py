from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "ScoutAI API"
    APP_ENV: str = "local"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"
    DATABASE_URL: str = (
        "postgresql+psycopg://scoutai:scoutai@localhost:5432/scoutai"
    )
    REDIS_URL: str = "redis://localhost:6379/0"
    LOG_LEVEL: str = "INFO"
    HACKER_NEWS_API_BASE_URL: str = "https://hacker-news.firebaseio.com/v0"
    HACKER_NEWS_REQUEST_TIMEOUT_SECONDS: int = Field(default=10, gt=0)
    HACKER_NEWS_MAX_CONCURRENCY: int = Field(default=8, gt=0)
    HACKER_NEWS_DEFAULT_LIMIT: int = Field(default=50, gt=0)
    HACKER_NEWS_MAX_LIMIT: int = Field(default=200, gt=0)
    HACKER_NEWS_DEFAULT_LOOKBACK_DAYS: int = Field(default=30, ge=1, le=365)
    COMPANY_ENRICHMENT_REQUEST_TIMEOUT_SECONDS: int = Field(default=10, gt=0)
    COMPANY_ENRICHMENT_MAX_REDIRECTS: int = Field(default=3, ge=0)
    COMPANY_ENRICHMENT_MAX_CANDIDATES_PER_RUN: int = Field(default=50, gt=0)
    COMPANY_ENRICHMENT_USER_AGENT: str = (
        "ScoutAI/0.1 company-domain-enrichment"
    )
    YC_COMPANY_RESOLVER_ENABLED: bool = True
    YC_COMPANY_BASE_URL: str = "https://www.ycombinator.com/companies"
    YC_COMPANY_REQUEST_TIMEOUT_SECONDS: int = Field(default=10, gt=0)
    YC_COMPANY_MAX_RETRIES: int = Field(default=2, ge=0)
    YC_COMPANY_USER_AGENT: str = "ScoutAI/0.1 YC-company-resolver"
    ASHBY_RESOLVER_ENABLED: bool = True
    ASHBY_POSTING_API_BASE_URL: str = (
        "https://api.ashbyhq.com/posting-api/job-board"
    )
    ASHBY_REQUEST_TIMEOUT_SECONDS: int = Field(default=10, gt=0)
    ASHBY_MAX_RETRIES: int = Field(default=2, ge=0)
    ASHBY_MAX_RESPONSE_BYTES: int = Field(default=2_000_000, gt=0)
    ASHBY_USER_AGENT: str = "ScoutAI/0.1 Ashby-public-job-resolver"
    ASHBY_INCLUDE_COMPENSATION: bool = True
    DISCOVERY_JOB_INGESTION_MAX_CANDIDATES_PER_RUN: int = Field(default=100, gt=0)

    @model_validator(mode="after")
    def validate_hacker_news_limits(self):
        if self.HACKER_NEWS_DEFAULT_LIMIT > self.HACKER_NEWS_MAX_LIMIT:
            self.HACKER_NEWS_DEFAULT_LIMIT = self.HACKER_NEWS_MAX_LIMIT
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
