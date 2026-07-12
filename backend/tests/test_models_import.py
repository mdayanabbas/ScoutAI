def test_all_models_importable():
    from app.models import (
        AgentRun,
        AgentStep,
        Company,
        CompanyPage,
        CrawlRun,
        DiscoveryCandidate,
        DiscoveryEvidence,
        DiscoveryRun,
        Job,
        JobBoardExpansionLink,
        JobEnrichmentAttempt,
        JobDiscoveryLink,
        JobMatchingProfile,
        TechStackItem,
        UserProfile,
    )

    assert all(
        [
            AgentRun,
            AgentStep,
            Company,
            CompanyPage,
            CrawlRun,
            DiscoveryCandidate,
            DiscoveryEvidence,
            DiscoveryRun,
            Job,
            JobBoardExpansionLink,
            JobEnrichmentAttempt,
            JobDiscoveryLink,
            JobMatchingProfile,
            TechStackItem,
            UserProfile,
        ]
    )
