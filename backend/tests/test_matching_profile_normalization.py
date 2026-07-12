import pytest

from app.core.errors import ValidationAppError
from app.matching.profile_normalization import (
    normalize_currency,
    normalize_profile_list,
    normalize_remote_type,
    normalize_role_category,
    normalize_skill_entries,
    normalize_skill_name,
    normalize_target_title,
    normalize_technology_name,
)


def test_profile_list_normalization_trims_dedupes_preserves_order_and_acronyms():
    values = [" Backend Engineer ", "backend engineer", "AI engineer", "ai engineer"]

    assert normalize_profile_list(
        values,
        normalize_target_title,
        maximum=10,
        field_name="target_titles",
    ) == ["Backend Engineer", "AI Engineer"]


def test_skill_and_technology_names_do_not_merge_partial_matches():
    assert normalize_skill_name("Java") == "Java"
    assert normalize_skill_name("JavaScript") == "JavaScript"
    assert normalize_technology_name("React") == "React"
    assert normalize_technology_name("React Native") == "React Native"


def test_duplicate_skills_merge_highest_years_and_proficiency():
    result = normalize_skill_entries(
        [
            {"name": "Python", "proficiency": "intermediate", "years_experience": 2},
            {"name": " python ", "proficiency": "advanced", "years_experience": 3},
        ],
        maximum=10,
        field_name="skills",
    )

    assert result == [{"name": "Python", "proficiency": "advanced", "years_experience": 3.0}]


def test_normalization_validates_values_and_limits():
    assert normalize_currency("usd") == "USD"
    assert normalize_remote_type("remote") == "remote_worldwide"
    assert normalize_role_category("machine_learning_engineer") == "ml_engineer"

    with pytest.raises(ValidationAppError):
        normalize_profile_list([""], normalize_target_title, maximum=10, field_name="target_titles")
    with pytest.raises(ValidationAppError):
        normalize_profile_list(["a", "b"], normalize_target_title, maximum=1, field_name="target_titles")
    with pytest.raises(ValidationAppError):
        normalize_skill_entries([{"name": "Python", "years_experience": -1}], maximum=10, field_name="skills")

