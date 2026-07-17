from sqlalchemy import Enum, inspect

from app.models.company_watchlist import CompanyWatchlistItem


def test_company_watchlist_model_table_indexes_and_no_native_enums():
    assert CompanyWatchlistItem.__tablename__ == "company_watchlist_items"
    columns = CompanyWatchlistItem.__table__.c
    assert columns.watch_status.type.length == 32
    assert columns.priority.type.length == 16
    assert not isinstance(columns.watch_status.type, Enum)

    index_names = {index.name for index in CompanyWatchlistItem.__table__.indexes}
    assert "ix_company_watchlist_items_company_id" in index_names
    assert "ix_company_watchlist_items_normalized_company_name" in index_names
    assert "ix_company_watchlist_items_normalized_domain" in index_names
    assert "ix_company_watchlist_items_watch_status" in index_names
    assert "ix_company_watchlist_items_priority" in index_names
    assert "ix_company_watchlist_items_created_at" in index_names
    assert "ix_company_watchlist_items_updated_at" in index_names


def test_company_watchlist_table_exists_in_metadata(db_session):
    assert "company_watchlist_items" in inspect(db_session.bind).get_table_names()

