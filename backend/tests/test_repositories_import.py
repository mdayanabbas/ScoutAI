def test_core_repositories_importable():
    from app.repositories import (
        AgentRunRepository,
        AgentStepRepository,
        BaseRepository,
        CompanyPageRepository,
        CompanyRepository,
        CrawlRunRepository,
        JobRepository,
        TechStackRepository,
        UserProfileRepository,
    )

    assert all(
        [
            AgentRunRepository,
            AgentStepRepository,
            BaseRepository,
            CompanyPageRepository,
            CompanyRepository,
            CrawlRunRepository,
            JobRepository,
            TechStackRepository,
            UserProfileRepository,
        ]
    )
