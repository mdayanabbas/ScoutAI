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
        JobEnrichmentAttempt,
        JobDiscoveryLink,
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
            JobEnrichmentAttempt,
            JobDiscoveryLink,
            TechStackItem,
            UserProfile,
        ]
    )
