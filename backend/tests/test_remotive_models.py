from app.discovery.sources.remotive.models import parse_remotive_jobs_response


def test_remotive_response_envelope_parses_aliases_and_optional_fields():
    parsed = parse_remotive_jobs_response(
        {
            "0-legal-notice": "legal",
            "job-count": "2",
            "jobs": [
                {
                    "id": 123,
                    "url": "https://remotive.com/remote-jobs/software-dev/ai-engineer-123",
                    "title": "AI Engineer",
                    "company_name": "Remote AI Co",
                    "job_type": "full_time",
                    "publication_date": "2026-07-14T10:00:00",
                    "candidate_required_location": "Worldwide",
                    "salary": "$80k - $120k yearly",
                },
                {"id": "bad", "company_name": "Missing Title"},
            ],
        },
        status_code=200,
        response_size=100,
    )

    assert parsed.legal_notice == "legal"
    assert parsed.job_count == 2
    assert parsed.jobs[0].source_id == "123"
    assert parsed.jobs[0].salary_text == "$80k - $120k yearly"
    assert parsed.jobs[0].publication_date is not None
    assert parsed.malformed_jobs[0].reason == "missing_title"


def test_remotive_response_rejects_malformed_envelopes():
    assert parse_remotive_jobs_response([]).reason == "remotive_invalid_envelope"
    assert parse_remotive_jobs_response({"job-count": 1}).reason == "remotive_invalid_envelope"
    assert parse_remotive_jobs_response({"job-count": "nope", "jobs": []}).reason == "remotive_invalid_envelope"


def test_remotive_response_tolerates_missing_legal_notice_and_optional_fields():
    parsed = parse_remotive_jobs_response(
        {"job-count": 1, "jobs": [{"id": 1, "title": "SWE", "company_name": "Code Co"}]}
    )

    assert parsed.legal_notice is None
    assert parsed.jobs[0].url is None
    assert parsed.jobs[0].job_type is None
