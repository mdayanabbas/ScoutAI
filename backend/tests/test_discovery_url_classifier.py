from app.discovery.url_classifier import CandidateUrlType, classify_candidate_url


def test_github_repository_url_classification():
    result = classify_candidate_url("https://github.com/rowboatlabs/rowboat")

    assert result.url_type == CandidateUrlType.GITHUB_REPOSITORY
    assert result.platform == "github"
    assert result.external_repository == "rowboatlabs/rowboat"
    assert result.first_party_url is None


def test_yc_job_url_classification():
    result = classify_candidate_url(
        "https://www.ycombinator.com/companies/infracost/jobs/abc"
    )

    assert result.url_type == CandidateUrlType.YC_JOB
    assert result.platform == "ycombinator"
    assert result.external_company_slug == "infracost"


def test_ashby_greenhouse_and_lever_url_classification():
    ashby = classify_candidate_url("https://jobs.ashbyhq.com/lago")
    greenhouse = classify_candidate_url("https://boards.greenhouse.io/supabase")
    lever = classify_candidate_url("https://jobs.lever.co/acme")

    assert ashby.url_type == CandidateUrlType.ASHBY_JOB
    assert ashby.external_company_slug == "lago"
    assert greenhouse.url_type == CandidateUrlType.GREENHOUSE_JOB
    assert greenhouse.external_company_slug == "supabase"
    assert lever.url_type == CandidateUrlType.LEVER_JOB
    assert lever.external_company_slug == "acme"


def test_first_party_careers_url_classification():
    result = classify_candidate_url("https://9mothers.com/careers")

    assert result.url_type == CandidateUrlType.FIRST_PARTY
    assert result.first_party_url == "https://9mothers.com/careers"
    assert result.is_first_party_company_domain is True
