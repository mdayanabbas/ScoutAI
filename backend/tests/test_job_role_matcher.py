from types import SimpleNamespace

from app.matching.role_matcher import TargetRoleMatcher


def match(title: str, role_category: str | None = None):
    job = SimpleNamespace(title=title, role_category=role_category, description="")
    profile = SimpleNamespace(excluded_titles_json=[], excluded_role_categories_json=[])
    return TargetRoleMatcher().match(job, profile)


def test_target_role_matches_and_aliases():
    assert match("AI Engineer").match_type == "exact"
    assert match("Applied AI Engineer").canonical_role == "ai_engineer"
    assert match("ML Engineer").canonical_role == "machine_learning_engineer"
    assert match("Machine Learning Engineer").match_type == "exact"
    assert match("Forward Deployed Engineer").canonical_role == "forward_deployed_engineer"
    assert match("FDE").match_type == "alias"
    assert match("Software Engineer").canonical_role == "software_engineer"
    assert match("SDE").match_type == "alias"
    assert match("SWE").match_type == "alias"


def test_adjacent_and_excluded_engineering_roles():
    assert match("Backend Engineer").match_type == "adjacent"
    assert match("Full Stack Engineer").match_type == "adjacent"
    for title in ("Electrical Engineer", "Robotics Engineer", "Perception Engineer", "Embedded Engineer", "Sales Engineer", "Solutions Engineer"):
        result = match(title)
        assert result.match_type == "excluded"
        assert result.score == 0
    assert match("Embedded Software Engineer").matched is True
    assert match("Robotics Software Engineer").matched is True
