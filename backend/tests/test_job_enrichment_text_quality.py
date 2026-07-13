from app.utils.text import (
    repair_mojibake,
    should_replace_job_title,
    strip_job_title_action_suffix,
)


def test_repair_mojibake_common_sequences_and_idempotence():
    cases = {
        "YouÃ¢â‚¬â„¢ll build": "You\u2019ll build",
        "Ã¢â‚¬Å“helloÃ¢â‚¬ï¿½": "\u201chello\u201d",
        "AÃ¢â‚¬â€œB": "A\u2013B",
        "AÃ¢â‚¬â€B": "A\u2014B",
        "Ã¢â€šÂ¬100": "\u20ac100",
    }
    for corrupted, expected in cases.items():
        repaired = repair_mojibake(corrupted)
        assert repaired == expected
        assert repair_mojibake(repaired) == expected


def test_repair_mojibake_preserves_clean_text_and_never_crashes():
    assert repair_mojibake("You'll build APIs – safely") == "You'll build APIs – safely"
    assert repair_mojibake("Plain ASCII") == "Plain ASCII"
    assert repair_mojibake("\x00\x01Ã(")


def test_strip_job_title_action_suffix_preserves_meaningful_words():
    assert strip_job_title_action_suffix("R&D Test Engineer, Senior Apply") == "R&D Test Engineer, Senior"
    assert strip_job_title_action_suffix("Electrical Engineer, Staff Apply Now") == "Electrical Engineer, Staff"
    assert strip_job_title_action_suffix("Backend Engineer View Role") == "Backend Engineer"
    assert strip_job_title_action_suffix("Applied Scientist") == "Applied Scientist"
    assert strip_job_title_action_suffix("Application Engineer") == "Application Engineer"
    assert strip_job_title_action_suffix("Details Engineer") == "Details Engineer"


def test_should_replace_job_title_quality_rules():
    assert should_replace_job_title("SWE", "Software Engineer", 0.98, "h1")
    assert should_replace_job_title("Open Roles", "Full Stack Engineer (TS/SCI)", 0.98, "h1")
    assert should_replace_job_title("Developer Advocate", "Developer Advocate & Partnerships (DevRel)", 0.98, "h1")
    assert should_replace_job_title("Largest Government Contract", "Full Stack Engineer (TS/SCI)", 0.98, "h1")
    assert not should_replace_job_title("Staff Platform Engineer", "Backend Engineer", 0.98, "h1")
    assert not should_replace_job_title("Staff Platform Engineer", "Backend Engineer", 0.7, "url_slug")
