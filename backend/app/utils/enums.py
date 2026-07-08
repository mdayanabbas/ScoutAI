from enum import StrEnum


class CompanyStage(StrEnum):
    UNKNOWN = "unknown"
    PRE_SEED = "pre_seed"
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    GROWTH = "growth"
    PUBLIC = "public"


class CompanySource(StrEnum):
    MANUAL = "manual"
    YC = "yc"
    PRODUCT_HUNT = "product_hunt"
    HACKER_NEWS = "hacker_news"
    WELLFOUND = "wellfound"
    COMPANY_WEBSITE = "company_website"
    RSS = "rss"
    OTHER = "other"


class DiscoverySource(StrEnum):
    MANUAL = "manual"
    HACKER_NEWS = "hacker_news"
    PRODUCT_HUNT = "product_hunt"
    YC = "yc"
    WELLFOUND = "wellfound"
    VC_PORTFOLIO = "vc_portfolio"
    RSS = "rss"
    NEWSLETTER = "newsletter"
    COMPANY_DIRECTORY = "company_directory"
    OTHER = "other"


class DiscoveryRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class DiscoveryCandidateStatus(StrEnum):
    DISCOVERED = "discovered"
    NORMALIZED = "normalized"
    DUPLICATE = "duplicate"
    REJECTED = "rejected"
    INGESTED = "ingested"
    FAILED = "failed"


class DiscoveryDecision(StrEnum):
    CREATED_COMPANY = "created_company"
    MATCHED_EXISTING_COMPANY = "matched_existing_company"
    DEFERRED = "deferred"
    REJECTED = "rejected"
    FAILED = "failed"


class PageType(StrEnum):
    HOMEPAGE = "homepage"
    ABOUT = "about"
    CAREERS = "careers"
    JOBS = "jobs"
    TEAM = "team"
    BLOG = "blog"
    ENGINEERING = "engineering"
    DOCS = "docs"
    PRICING = "pricing"
    UNKNOWN = "unknown"


class RemoteType(StrEnum):
    UNKNOWN = "unknown"
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE_COUNTRY = "remote_country"
    REMOTE_REGION = "remote_region"
    REMOTE_WORLDWIDE = "remote_worldwide"


class JobStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class RoleCategory(StrEnum):
    AI_ENGINEER = "ai_engineer"
    BACKEND_ENGINEER = "backend_engineer"
    SOFTWARE_ENGINEER = "software_engineer"
    ML_ENGINEER = "ml_engineer"
    DATA_ENGINEER = "data_engineer"
    FULL_STACK_ENGINEER = "full_stack_engineer"
    FRONTEND_ENGINEER = "frontend_engineer"
    DEVOPS_ENGINEER = "devops_engineer"
    PRODUCT_ENGINEER = "product_engineer"
    OTHER = "other"


class CrawlStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
