def test_services_importable():
    from app.services import (
        AgentRunService,
        CompanyPageService,
        CompanyService,
        CrawlRunService,
        DiscoveryService,
        HimalayasRemoteJobDiscoveryService,
        JobApplicationDecisionService,
        WeWorkRemotelyDiscoveryService,
        RemotiveRemoteJobDiscoveryService,
        RemoteJobDiscoveryOrchestratorService,
        JobMatchingService,
        JobMatchingProfileService,
        JobService,
        TechStackService,
        UserProfileService,
    )

    assert all(
        [
            AgentRunService,
            CompanyPageService,
            CompanyService,
            CrawlRunService,
            DiscoveryService,
            HimalayasRemoteJobDiscoveryService,
            JobApplicationDecisionService,
            WeWorkRemotelyDiscoveryService,
            RemotiveRemoteJobDiscoveryService,
            RemoteJobDiscoveryOrchestratorService,
            JobMatchingService,
            JobMatchingProfileService,
            JobService,
            TechStackService,
            UserProfileService,
        ]
    )
