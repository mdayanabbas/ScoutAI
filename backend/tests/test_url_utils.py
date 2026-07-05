from app.utils.urls import extract_domain, normalize_domain, normalize_url


def test_normalize_url_removes_protocol_www_and_trailing_slash():
    assert normalize_url("https://www.acme.ai/") == "acme.ai"
    assert normalize_url("http://www.acme.ai/jobs/") == "acme.ai/jobs"


def test_extract_and_normalize_domain():
    assert extract_domain("http://acme.ai/jobs") == "acme.ai"
    assert normalize_domain("https://www.acme.ai/") == "acme.ai"
    assert normalize_domain("acme.ai") == "acme.ai"


def test_url_utils_handle_empty_input_safely():
    assert normalize_url("") == ""
    assert extract_domain("") == ""
    assert normalize_domain("") == ""
