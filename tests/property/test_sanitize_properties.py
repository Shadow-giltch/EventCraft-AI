from hypothesis import given, settings
from hypothesis import strategies as st

from eventcraft.security.sanitize import has_control_characters, sanitize_string


@settings(max_examples=50)
@given(text=st.text(max_size=300))
def test_sanitize_is_idempotent_and_clean(text: str):
    first_pass = sanitize_string(text)
    second_pass = sanitize_string(first_pass)
    # Idempotent
    assert first_pass == second_pass
    # Free of control characters
    assert has_control_characters(first_pass) is False
