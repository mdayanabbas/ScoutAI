def test_core_schemas_importable():
    from app.schemas import (
        AgentRunCreate,
        AgentStepCreate,
        CompanyCreate,
        CompanyPageCreate,
        CrawlRunCreate,
        DiscoveryRunResult,
        ManualDiscoveryRequest,
        JobBatchEnrichmentRead,
        JobBatchEnrichmentRequest,
        JobCreate,
        JobEnrichmentAttemptListRead,
        JobEnrichmentAttemptRead,
        JobEnrichmentRunRead,
        JobSourceDetectionRead,
        PaginatedResponse,
        TechStackItemCreate,
        UserProfileCreate,
    )

    assert all(
        [
            AgentRunCreate,
            AgentStepCreate,
            CompanyCreate,
            CompanyPageCreate,
            CrawlRunCreate,
            DiscoveryRunResult,
            ManualDiscoveryRequest,
            JobBatchEnrichmentRead,
            JobBatchEnrichmentRequest,
            JobCreate,
            JobEnrichmentAttemptListRead,
            JobEnrichmentAttemptRead,
            JobEnrichmentRunRead,
            JobSourceDetectionRead,
            PaginatedResponse,
            TechStackItemCreate,
            UserProfileCreate,
        ]
    )
