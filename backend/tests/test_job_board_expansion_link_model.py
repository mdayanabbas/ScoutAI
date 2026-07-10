from sqlalchemy import inspect

from app.models.job_board_expansion_link import JobBoardExpansionLink


def test_job_board_expansion_link_metadata():
    table = JobBoardExpansionLink.__table__

    assert table.c.provider.type.length >= 64
    assert {column.name for column in table.c} >= {
        "parent_job_id",
        "child_job_id",
        "discovery_candidate_id",
        "provider",
    }
    assert "uq_job_board_expansion_links_parent_child" in {
        constraint.name for constraint in table.constraints
    }
    assert "ck_job_board_expansion_links_not_self" in {
        constraint.name for constraint in table.constraints
    }
    assert inspect(JobBoardExpansionLink).relationships["parent_job"]

