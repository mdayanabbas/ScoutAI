from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ENV_FILE,
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
    YC_JOB_REQUEST_TIMEOUT_SECONDS: int = Field(default=10, gt=0)
    YC_JOB_MAX_REDIRECTS: int = Field(default=3, ge=0)
    YC_JOB_MAX_RESPONSE_BYTES: int = Field(default=2_000_000, gt=0)
    YC_JOB_USER_AGENT: str = "ScoutAI/0.1 job-enrichment"
    YC_JOB_MAX_RETRIES: int = Field(default=1, ge=0)
    ASHBY_JOB_PUBLIC_API_BASE_URL: str = "https://api.ashbyhq.com/posting-api/job-board"
    ASHBY_JOB_REQUEST_TIMEOUT_SECONDS: int = Field(default=10, gt=0)
    ASHBY_JOB_MAX_RETRIES: int = Field(default=1, ge=0)
    ASHBY_JOB_MAX_RESPONSE_BYTES: int = Field(default=4_000_000, gt=0)
    ASHBY_JOB_USER_AGENT: str = "ScoutAI/0.1 job-enrichment"
    ASHBY_JOB_MAX_POSTINGS_PER_BOARD: int = Field(default=200, gt=0)
    ASHBY_JOB_MATCH_MIN_CONFIDENCE: float = Field(default=0.90, ge=0, le=1)
    ASHBY_JOB_MATCH_MIN_GAP: float = Field(default=0.10, ge=0, le=1)
    ASHBY_BOARD_EXPANSION_MAX_POSTINGS: int = Field(default=200, gt=0)
    ASHBY_BOARD_EXPANSION_MIN_MATCH_SCORE: float = Field(default=0.75, ge=0, le=1)
    ASHBY_BOARD_EXPANSION_MIN_SCORE_GAP: float = Field(default=0.10, ge=0, le=1)
    ASHBY_BOARD_EXPANSION_MAX_CREATE: int = Field(default=25, gt=0)
    ASHBY_BOARD_EXPANSION_ALLOW_BROAD_HIRING: bool = True
    FIRST_PARTY_JOB_REQUEST_TIMEOUT_SECONDS: int = Field(default=10, gt=0)
    FIRST_PARTY_JOB_MAX_REDIRECTS: int = Field(default=5, ge=0)
    FIRST_PARTY_JOB_MAX_RETRIES: int = Field(default=1, ge=0)
    FIRST_PARTY_JOB_MAX_RESPONSE_BYTES: int = Field(default=2_000_000, gt=0)
    FIRST_PARTY_JOB_USER_AGENT: str = "ScoutAI/0.1 job-enrichment"
    FIRST_PARTY_JOB_RESPECT_ROBOTS: bool = True
    FIRST_PARTY_JOB_MAX_DESCRIPTION_CHARS: int = Field(default=30_000, gt=0)
    FIRST_PARTY_JOB_ALLOWED_CONTENT_TYPES: str = "text/html,application/xhtml+xml"
    FIRST_PARTY_LISTING_MAX_LINKS: int = Field(default=100, gt=0)
    FIRST_PARTY_LISTING_MAX_CREATE: int = Field(default=25, gt=0)
    FIRST_PARTY_LISTING_MAX_DETAIL_FETCHES: int = Field(default=25, ge=0)
    FIRST_PARTY_LISTING_MIN_LINK_CONFIDENCE: float = Field(default=0.75, ge=0, le=1)
    FIRST_PARTY_LISTING_MIN_SCOPE_SCORE: float = Field(default=0.70, ge=0, le=1)
    FIRST_PARTY_LISTING_ALLOW_BROAD_HIRING: bool = True
    FIRST_PARTY_LISTING_REQUIRE_SAME_DOMAIN_DETAILS: bool = True
    FIRST_PARTY_LISTING_DELAY_MS: int = Field(default=0, ge=0)
    JOB_ENRICHMENT_BATCH_DEFAULT_LIMIT: int = Field(default=10, ge=1)
    JOB_ENRICHMENT_BATCH_MAX_LIMIT: int = Field(default=50, ge=1)
    JOB_ENRICHMENT_BATCH_DELAY_MS: int = Field(default=0, ge=0)
    ASHBY_RESOLVER_ENABLED: bool = True
    ASHBY_POSTING_API_BASE_URL: str = (
        "https://api.ashbyhq.com/posting-api/job-board"
    )
    ASHBY_REQUEST_TIMEOUT_SECONDS: int = Field(default=10, gt=0)
    ASHBY_MAX_RETRIES: int = Field(default=2, ge=0)
    ASHBY_MAX_RESPONSE_BYTES: int = Field(default=2_000_000, gt=0)
    ASHBY_USER_AGENT: str = "ScoutAI/0.1 Ashby-public-job-resolver"
    ASHBY_INCLUDE_COMPENSATION: bool = True
    WEB_SEARCH_PROVIDER: str = "tavily"
    WEB_SEARCH_ENABLED: bool = False
    WEB_SEARCH_MAX_QUERIES_PER_CANDIDATE: int = Field(default=2, ge=1, le=10)
    WEB_SEARCH_RESULTS_PER_QUERY: int = Field(default=5, ge=1, le=20)
    WEB_SEARCH_REQUEST_TIMEOUT_SECONDS: int = Field(default=10, gt=0)
    WEB_SEARCH_MAX_RETRIES: int = Field(default=2, ge=0)
    WEB_SEARCH_MAX_RESPONSE_BYTES: int = Field(default=1_000_000, gt=0)
    TAVILY_API_KEY: str | None = None
    TAVILY_SEARCH_BASE_URL: str = "https://api.tavily.com/search"
    TAVILY_SEARCH_DEPTH: str = "basic"
    TAVILY_USER_AGENT: str = "ScoutAI/0.1 company-identity-search"
    BRAVE_SEARCH_API_KEY: str | None = None
    BRAVE_SEARCH_BASE_URL: str = "https://api.search.brave.com/res/v1/web/search"
    BRAVE_SEARCH_USER_AGENT: str = "ScoutAI/0.1 company-identity-search"
    DISCOVERY_JOB_INGESTION_MAX_CANDIDATES_PER_RUN: int = Field(default=100, gt=0)
    HIMALAYAS_DISCOVERY_ENABLED: bool = True
    HIMALAYAS_API_BASE_URL: str = "https://himalayas.app"
    HIMALAYAS_SEARCH_PATH: str = "/jobs/api/search"
    HIMALAYAS_REQUEST_TIMEOUT_SECONDS: int = Field(default=15, gt=0)
    HIMALAYAS_MAX_RETRIES: int = Field(default=1, ge=0)
    HIMALAYAS_MAX_QUERIES_PER_RUN: int = Field(default=12, ge=1, le=50)
    HIMALAYAS_MAX_PAGES_PER_QUERY: int = Field(default=3, ge=1, le=10)
    HIMALAYAS_REQUEST_DELAY_MS: int = Field(default=250, ge=0)
    HIMALAYAS_DISCOVERY_COOLDOWN_HOURS: int = Field(default=24, ge=0)
    HIMALAYAS_MAX_JOBS_PER_RUN: int = Field(default=100, ge=1, le=500)
    HIMALAYAS_SCORE_AFTER_INGESTION: bool = True
    HIMALAYAS_STORE_REJECTED_CANDIDATES: bool = True
    WWR_DISCOVERY_ENABLED: bool = True
    WWR_PROGRAMMING_RSS_URL: str = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
    WWR_ALL_OTHER_RSS_URL: str = "https://weworkremotely.com/categories/all-other-remote-jobs.rss"
    WWR_INCLUDE_ALL_OTHER_FEED: bool = True
    WWR_REQUEST_TIMEOUT_SECONDS: int = Field(default=15, gt=0)
    WWR_MAX_RETRIES: int = Field(default=1, ge=0)
    WWR_MAX_RESPONSE_BYTES: int = Field(default=5_000_000, gt=0)
    WWR_DISCOVERY_COOLDOWN_HOURS: int = Field(default=6, ge=0)
    WWR_MAX_ITEMS_PER_FEED: int = Field(default=200, ge=1, le=500)
    WWR_MAX_JOBS_PER_RUN: int = Field(default=100, ge=1, le=500)
    WWR_SCORE_AFTER_INGESTION: bool = True
    WWR_STORE_REJECTED_CANDIDATES: bool = True
    WWR_USE_CONDITIONAL_REQUESTS: bool = True
    WWR_MAX_JOB_AGE_DAYS: int = Field(default=45, ge=1, le=365)

    @model_validator(mode="after")
    def validate_hacker_news_limits(self):
        if self.HACKER_NEWS_DEFAULT_LIMIT > self.HACKER_NEWS_MAX_LIMIT:
            self.HACKER_NEWS_DEFAULT_LIMIT = self.HACKER_NEWS_MAX_LIMIT
        if self.JOB_ENRICHMENT_BATCH_DEFAULT_LIMIT > self.JOB_ENRICHMENT_BATCH_MAX_LIMIT:
            self.JOB_ENRICHMENT_BATCH_DEFAULT_LIMIT = self.JOB_ENRICHMENT_BATCH_MAX_LIMIT
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
