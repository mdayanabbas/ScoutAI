from app.discovery.hacker_news_job_parser import (
    extract_job_location,
    extract_job_title,
    extract_remote_signal,
    is_hacker_news_hiring_candidate,
    select_job_url,
)
from app.models.discovery_candidate import DiscoveryCandidate
from app.utils.enums import DiscoveryCandidateStatus, DiscoveryDecision, DiscoverySource, RemoteType


def _candidate(title: str, text: str = "", url: str | None = None):
    return DiscoveryCandidate(
        discovery_run_id="run",
        source=DiscoverySource.HACKER_NEWS,
        source_identifier="hn:1",
        raw_name=title,
        raw_description=text,
        normalized_name=title,
        normalized_description=text,
        status=DiscoveryCandidateStatus.INGESTED,
        decision=DiscoveryDecision.CREATED_COMPANY,
        matched_company_id="company",
        raw_payload={"id": 1, "type": "job", "feed": "jobs", "title": title, "url": url},
    )


def test_hacker_news_hiring_eligibility():
    assert is_hacker_news_hiring_candidate(_candidate("Acme Is Hiring")) is True
    show = _candidate("Show HN: Acme", url="https://acme.ai")
    show.raw_payload = {"id": 2, "type": "story", "feed": "show", "title": "Show HN: Acme"}
    show.evidence = []
    assert is_hacker_news_hiring_candidate(show) is False


def test_title_parsing_examples():
    assert extract_job_title(_candidate("Dexter (YC F24) Is Hiring a Founding Engineer in Berlin")) == "Founding Engineer"
    assert extract_job_title(_candidate("Infracost (YC W21) Is Hiring a Marketing Lead to Shift FinOps Left")) == "Marketing Lead"
    assert extract_job_title(_candidate("Manufact (YC S25) Is Hiring a Developer Advocate in SF")) == "Developer Advocate"
    assert extract_job_title(_candidate("Nox Metals (YC S25) Is Hiring SWE")) == "SWE"
    assert extract_job_title(_candidate("9 Mothers (YC P26) Is Hiring in Austin, TX")) == "Open Roles"
    assert extract_job_title(_candidate("Lago (YC S21) Is Hiring for Our GTM Team")) == "GTM Team Roles"


def test_location_parsing_examples():
    assert extract_job_location(_candidate("Dexter (YC F24) Is Hiring a Founding Engineer in Berlin")) == "Berlin"
    assert extract_job_location(_candidate("9 Mothers (YC P26) Is Hiring in Austin, TX")) == "Austin, TX"
    assert extract_job_location(_candidate("Manufact (YC S25) Is Hiring a Developer Advocate in SF")) == "SF"
    assert extract_job_location(_candidate("Acme Is Hiring", "Location: San Francisco, CA")) == "San Francisco, CA"


def test_remote_signal_is_conservative():
    assert extract_remote_signal(_candidate("Acme Is Hiring", "Fully remote role")) == RemoteType.REMOTE_WORLDWIDE
    assert extract_remote_signal(_candidate("Dexter Is Hiring", "Berlin, on-site at least 4 days a week")) == RemoteType.ONSITE
    assert extract_remote_signal(_candidate("Dexter Is Hiring", "Not a good fit if you prefer to work remotely")) == RemoteType.UNKNOWN


def test_job_url_selection():
    assert select_job_url(_candidate("Acme Is Hiring", url="https://jobs.ashbyhq.com/acme")) == "https://jobs.ashbyhq.com/acme"
    assert select_job_url(_candidate("Dexter Is Hiring", "Apply at https://www.ycombinator.com/companies/dexter/jobs/1", None)).startswith("https://www.ycombinator.com")
    assert select_job_url(_candidate("Fallback Is Hiring", "", None)) == "https://news.ycombinator.com/item?id=1"
