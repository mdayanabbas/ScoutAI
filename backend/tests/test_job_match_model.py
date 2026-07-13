import sqlalchemy as sa

import app.models  # noqa: F401
from app.db.base import Base
from app.models import JobMatch


def _has_unique_constraint(table: sa.Table, column_names: set[str]) -> bool:
    return any(isinstance(item, sa.UniqueConstraint) and set(item.columns.keys()) == column_names for item in table.constraints)


def test_job_match_model_registered_and_constraints():
    table = Base.metadata.tables["job_matches"]

    assert JobMatch
    assert _has_unique_constraint(table, {"job_id", "job_matching_profile_id"})
    assert {"job_id", "job_matching_profile_id", "eligibility_status", "total_score", "scored_at"}.issubset(table.columns.keys())
    assert {"jobs", "job_matching_profiles"} == {fk.column.table.name for fk in table.foreign_keys}
