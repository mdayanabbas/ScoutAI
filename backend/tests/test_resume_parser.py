from app.resume.parser import ResumeParser


def test_parser_extracts_sections_and_known_technologies_without_unsafe_fuzzy_matching():
    text = """
    Summary
    Backend AI engineer.

    Technical Skills
    Python, FastAPI, PostgreSQL, Docker, LLMs, Java

    Projects
    RAG job matching platform with OpenAI and SQLAlchemy.

    Experience
    Built APIs and evaluation workflows.

    Education
    B.Tech Computer Science

    Links
    https://github.com/abbas/scoutai
    """

    parsed = ResumeParser().parse(text)

    assert "Python" in parsed.technologies
    assert "FastAPI" in parsed.technologies
    assert "PostgreSQL" in parsed.technologies
    assert "Docker" in parsed.technologies
    assert "LLMs" in parsed.technologies
    assert "JavaScript" not in parsed.technologies
    assert parsed.projects
    assert parsed.experience
    assert parsed.education
    assert parsed.links
