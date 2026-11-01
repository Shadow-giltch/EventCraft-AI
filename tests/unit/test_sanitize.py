from eventcraft.security.sanitize import has_control_characters, sanitize_string


def test_has_control_characters():
    assert has_control_characters("Valid string") is False
    assert has_control_characters("Invalid\x00string") is True
    assert has_control_characters("Bidi\u202etest") is True


def test_sanitize_string():
    clean = sanitize_string("Clean text")
    assert clean == "Clean text"

    dirty = "Dirty\x00 text\u200b with \u202ebidi"
    sanitized = sanitize_string(dirty)
    assert has_control_characters(sanitized) is False
