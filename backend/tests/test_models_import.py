def test_all_models_importable():
    from app.models import (
        AgentRun,
        AgentStep,
        Company,
        CompanyPage,
        CrawlRun,
        Job,
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
            Job,
            TechStackItem,
            UserProfile,
        ]
    )
