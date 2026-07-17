import pytest
from pydantic import ValidationError

from app.schemas.company_watchlist import CompanyWatchlistCreate, CompanyWatchlistUpdate


def test_create_requires_company_id_or_company_name():
    with pytest.raises(ValidationError):
        CompanyWatchlistCreate()


def test_create_rejects_user_profile_id_and_defaults_work():
    with pytest.raises(ValidationError):
        CompanyWatchlistCreate(company_name="Tether", user_profile_id="abc")

    data = CompanyWatchlistCreate(company_name="Tether")
    assert data.watch_status == "watching"
    assert data.priority == "medium"
    assert data.remote_interest == "unknown"
    assert data.junior_friendliness_signal == "unknown"


def test_create_validates_enum_like_values_and_normalizes_empty_strings():
    with pytest.raises(ValidationError):
        CompanyWatchlistCreate(company_name="Tether", watch_status="bad")
    with pytest.raises(ValidationError):
        CompanyWatchlistCreate(company_name="Tether", priority="urgent")

    data = CompanyWatchlistCreate(company_name=" Tether ", notes="", tags=["ai", "", " remote "])
    assert data.notes is None
    assert data.tags == ["ai", "remote"]


def test_update_rejects_user_profile_id_and_cleans_lists():
    with pytest.raises(ValidationError):
        CompanyWatchlistUpdate(user_profile_id="abc")

    data = CompanyWatchlistUpdate(target_roles=[" AI Engineer ", ""])
    assert data.target_roles == ["AI Engineer"]

