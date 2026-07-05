from app.utils.text import normalize_text, normalize_title


def test_normalize_text_strips_and_collapses_whitespace():
    assert normalize_text("  hello   scout  ") == "hello scout"
    assert normalize_text(None) is None
    assert normalize_text("   ") is None


def test_normalize_title_lowercases_and_collapses_whitespace():
    assert normalize_title("  Senior   AI Engineer  ") == "senior ai engineer"
