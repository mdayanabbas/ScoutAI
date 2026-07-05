def test_core_schemas_importable():
    from app.schemas import (
        AgentRunCreate,
        AgentStepCreate,
        CompanyCreate,
        CompanyPageCreate,
        CrawlRunCreate,
        JobCreate,
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
            JobCreate,
            PaginatedResponse,
            TechStackItemCreate,
            UserProfileCreate,
        ]
    )
