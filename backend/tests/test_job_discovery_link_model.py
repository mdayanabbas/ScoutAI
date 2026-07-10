import sqlalchemy as sa

import app.models  # noqa: F401
from app.db.base import Base
from app.models import JobDiscoveryLink


def _has_unique_constraint(table: sa.Table, column_names: set[str]) -> bool:
    for constraint in table.constraints:
        if isinstance(constraint, sa.UniqueConstraint):
            if set(constraint.columns.keys()) == column_names:
                return True
    return False


def test_job_discovery_link_model_is_registered():
    assert JobDiscoveryLink
    assert "job_discovery_links" in Base.metadata.tables


def test_job_discovery_link_table_shape():
    table = Base.metadata.tables["job_discovery_links"]

    assert {"id", "job_id", "discovery_candidate_id", "created_at", "updated_at"}.issubset(
        table.columns.keys()
    )
    assert _has_unique_constraint(table, {"job_id", "discovery_candidate_id"})
    assert _has_unique_constraint(table, {"discovery_candidate_id"})
    assert {fk.column.table.name for fk in table.foreign_keys} == {
        "jobs",
        "discovery_candidates",
    }
