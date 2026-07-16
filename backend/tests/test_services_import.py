def test_services_importable():
    from app.services import (
        AgentRunService,
        CompanyPageService,
        CompanyService,
        CrawlRunService,
        DiscoveryService,
        HimalayasRemoteJobDiscoveryService,
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
