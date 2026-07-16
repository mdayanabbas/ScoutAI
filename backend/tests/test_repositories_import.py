def test_core_repositories_importable():
    from app.repositories import (
        AgentRunRepository,
        AgentStepRepository,
        BaseRepository,
        CompanyPageRepository,
        CompanyRepository,
        CrawlRunRepository,
        DiscoveryCandidateRepository,
        DiscoveryEvidenceRepository,
        DiscoveryRunRepository,
        JobRepository,
        JobApplicationDecisionRepository,
        JobBoardExpansionLinkRepository,
        JobEnrichmentAttemptRepository,
        JobMatchRepository,
        JobMatchingProfileRepository,
        ResumeRepository,
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
            DiscoveryCandidateRepository,
            DiscoveryEvidenceRepository,
            DiscoveryRunRepository,
            JobRepository,
            JobApplicationDecisionRepository,
            JobBoardExpansionLinkRepository,
            JobEnrichmentAttemptRepository,
            JobMatchRepository,
            JobMatchingProfileRepository,
            ResumeRepository,
            TechStackRepository,
            UserProfileRepository,
        ]
    )
