"""Edge-case tests for allowed-origin handling in AppSettings."""

from pathlib import Path

import pytest

from eventcraft.config import AppSettings


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Run each test without the developer's real .env or origin variable."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)


def test_malformed_json_array_falls_back_to_comma_split() -> None:
    """A bracketed value that is not valid JSON is kept as a single raw item."""
    assert AppSettings(allowed_origins="[bad]").cors_origins == ["[bad]"]


def test_non_text_origin_value_is_wrapped_in_a_list() -> None:
    """A scalar that is neither text nor a collection becomes a one-item list."""
    assert AppSettings(allowed_origins=123).cors_origins == ["123"]


def test_cors_origins_wraps_a_plain_string(monkeypatch: pytest.MonkeyPatch) -> None:
    """cors_origins still returns a list if the raw attribute was set to a string."""
    settings = AppSettings()
    monkeypatch.setattr(settings, "allowed_origins", "http://example.com")
    assert settings.cors_origins == ["http://example.com"]
