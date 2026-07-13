from types import SimpleNamespace

from app.discovery.sources.himalayas.query_planner import HimalayasTargetedQueryPlanner


def test_query_planner_derives_and_deduplicates_profile_roles():
    profile = SimpleNamespace(
        target_titles_json=["SWE", "Software Engineer", "ML Engineer", "Sales Engineer"],
        target_role_categories_json=["ai_engineer"],
    )

    plan = HimalayasTargetedQueryPlanner().build_plan(profile, max_queries=3)

    assert len(plan.passes) == 3
    assert [item.query_type for item in plan.passes] == ["worldwide", "india", "worldwide"]
    assert plan.queries == ["AI Engineer", "Machine Learning Engineer"]
    assert "Sales Engineer" not in plan.queries


def test_query_planner_uses_safe_defaults_without_titles():
    plan = HimalayasTargetedQueryPlanner().build_plan(SimpleNamespace(target_titles_json=[], target_role_categories_json=[]), max_queries=5)

    assert len(plan.passes) == 5
    assert plan.queries[:3] == ["AI Engineer", "Machine Learning Engineer", "Forward Deployed Engineer"]
    assert plan.generated_from_profile is False


def test_query_planner_strict_query_pass_caps():
    profile = SimpleNamespace(target_titles_json=["AI Engineer", "ML Engineer"], target_role_categories_json=[])

    one = HimalayasTargetedQueryPlanner().build_plan(profile, max_queries=1)
    two = HimalayasTargetedQueryPlanner().build_plan(profile, max_queries=2)
    ten = HimalayasTargetedQueryPlanner().build_plan(profile, max_queries=10)

    assert len(one.passes) == 1
    assert one.passes[0].query_type == "worldwide"
    assert len(two.passes) == 2
    assert [item.query_type for item in two.passes] == ["worldwide", "india"]
    assert len(ten.passes) <= 10
