from app.enrichment.ashby_public_job_parser import parse_ashby_job_board


def test_parses_listed_public_job_and_ignores_unlisted_job():
    jobs = parse_ashby_job_board(
        {
            "jobs": [
                {
                    "id": "2e718684-4f75-4a99-8d6b-3b6bd44e4228",
                    "title": "Software Engineer",
                    "location": "Remote",
                    "secondaryLocations": [{"name": "London"}],
                    "department": "Engineering",
                    "team": {"name": "Database"},
                    "isListed": True,
                    "isRemote": True,
                    "workplaceType": "Remote",
                    "descriptionPlain": "Email careers@supabase.com",
                    "descriptionHtml": "<p>Email careers@supabase.com</p>",
                    "publishedAt": "2026-07-01T12:00:00Z",
                    "employmentType": "FullTime",
                    "jobUrl": (
                        "https://jobs.ashbyhq.com/supabase/"
                        "2e718684-4f75-4a99-8d6b-3b6bd44e4228"
                    ),
                    "applyUrl": (
                        "https://jobs.ashbyhq.com/supabase/"
                        "2e718684-4f75-4a99-8d6b-3b6bd44e4228/application"
                    ),
                    "compensation": {"summary": "$150k-$200k"},
                },
                {"title": "Hidden", "isListed": False},
            ]
        }
    )

    assert jobs is not None
    assert len(jobs) == 1
    job = jobs[0]
    assert job.title == "Software Engineer"
    assert job.location == "Remote"
    assert job.secondary_locations == ("London",)
    assert job.department == "Engineering"
    assert job.team == "Database"
    assert job.workplace_type == "Remote"
    assert job.employment_type == "FullTime"
    assert job.compensation_summary == "$150k-$200k"
    assert job.published_at is not None


def test_handles_missing_optional_fields_and_rejects_invalid_shape():
    jobs = parse_ashby_job_board({"jobs": [{"title": "Engineer"}]})

    assert jobs is not None
    assert jobs[0].location is None
    assert jobs[0].description_plain is None
    assert jobs[0].job_url is None
    assert parse_ashby_job_board({"not_jobs": []}) is None
