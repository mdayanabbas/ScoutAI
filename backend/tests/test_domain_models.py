import sqlalchemy as sa

import app.models  # noqa: F401
from app.db.base import Base

EXPECTED_TABLES = {
    "user_profiles",
    "companies",
    "company_pages",
    "jobs",
    "tech_stack_items",
    "crawl_runs",
    "agent_runs",
    "agent_steps",
}


def test_expected_tables_in_metadata():
    tables = set(Base.metadata.tables.keys())
    assert EXPECTED_TABLES.issubset(tables)


def test_company_table_has_required_columns():
    company = Base.metadata.tables["companies"]
    required = {
        "id",
        "name",
        "website_url",
        "normalized_domain",
        "description",
        "stage",
        "source",
        "is_active",
        "created_at",
        "updated_at",
    }
    assert required.issubset(company.columns.keys())


def test_company_normalized_domain_unique_index():
    company = Base.metadata.tables["companies"]
    normalized_domain_idx = next(
        idx for idx in company.indexes if idx.name == "ix_companies_normalized_domain"
    )
    assert normalized_domain_idx.unique is True


def _has_unique_constraint(table: sa.Table, column_names: set[str]) -> bool:
    for constraint in table.constraints:
        if isinstance(constraint, sa.UniqueConstraint):
            if set(constraint.columns.keys()) == column_names:
                return True
    return False


def test_company_page_unique_constraint_on_company_id_and_url():
    company_page = Base.metadata.tables["company_pages"]
    assert _has_unique_constraint(company_page, {"company_id", "url"})


def test_job_unique_constraint_on_company_id_and_job_url():
    job = Base.metadata.tables["jobs"]
    assert _has_unique_constraint(job, {"company_id", "job_url"})


def test_tech_stack_unique_constraint_on_company_name_source():
    tech_stack = Base.metadata.tables["tech_stack_items"]
    assert _has_unique_constraint(tech_stack, {"company_id", "name", "source"})


def test_agent_run_has_nullable_company_and_job_fks():
    agent_run = Base.metadata.tables["agent_runs"]
    assert agent_run.columns["company_id"].nullable is True
    assert agent_run.columns["job_id"].nullable is True


def test_agent_step_foreign_key_to_agent_runs():
    agent_step = Base.metadata.tables["agent_steps"]
    target_tables = {fk.column.table.name for fk in agent_step.foreign_keys}
    assert "agent_runs" in target_tables
