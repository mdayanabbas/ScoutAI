from types import SimpleNamespace

from app.discovery.sources.remotive.query_planner import RemotiveTargetedQueryPlanner


def test_planner_adds_software_category_and_priority_searches():
    profile = SimpleNamespace(target_titles_json=["AI Engineer", "ML Engineer", "FDE"], target_role_categories_json=[])

    plan = RemotiveTargetedQueryPlanner().build_plan(profile, max_requests=4, limit=200)

    assert plan.requests[0].request_type == "category"
    assert plan.requests[0].category == "software-dev"
    assert [item.search_term for item in plan.requests[1:]] == [
        "AI Engineer",
        "Machine Learning Engineer",
        "Forward Deployed Engineer",
    ]


def test_planner_deduplicates_aliases_and_respects_caps():
    profile = SimpleNamespace(target_titles_json=["SWE", "SDE", "Software Engineer"], target_role_categories_json=[])

    plan = RemotiveTargetedQueryPlanner().build_plan(profile, max_requests=1, limit=25)

    assert len(plan.requests) == 1
    assert plan.requests[0].request_type == "category"
    assert "remotive_request_cap_applied" in plan.warnings


def test_planner_uses_safe_defaults_for_missing_profile_terms_and_no_injection():
    profile = SimpleNamespace(target_titles_json=["https://evil.example?q=Sales"], target_role_categories_json=[])

    plan = RemotiveTargetedQueryPlanner().build_plan(profile, max_requests=3, limit=100)

    assert [item.search_term for item in plan.requests if item.search_term] == ["AI Engineer", "Machine Learning Engineer"]
    assert all("evil" not in str(item.search_term) for item in plan.requests)
