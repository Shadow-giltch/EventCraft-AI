"""Tests for allowed-origin parsing and lenient environment decoding."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from eventcraft.config import AppSettings


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Run each test without the developer's real .env or origin variable."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)


def test_comma_separated_origins_become_a_list() -> None:
    """A comma-separated string is split and trimmed."""
    settings = AppSettings(allowed_origins="http://a.com, http://b.com")
    assert settings.cors_origins == ["http://a.com", "http://b.com"]


def test_json_array_origins_are_parsed() -> None:
    """A JSON array string is accepted."""
    settings = AppSettings(allowed_origins='["http://a.com", "http://b.com"]')
    assert settings.cors_origins == ["http://a.com", "http://b.com"]


def test_list_origins_are_cleaned() -> None:
    """Blank list items are dropped."""
    settings = AppSettings(allowed_origins=["http://a.com", " ", "http://b.com"])
    assert settings.cors_origins == ["http://a.com", "http://b.com"]


def test_empty_origins_fall_back_to_defaults() -> None:
    """Empty input restores the safe local defaults."""
    assert AppSettings(allowed_origins="").cors_origins
    assert AppSettings(allowed_origins=[]).cors_origins


def test_wildcard_origin_is_rejected() -> None:
    """A wildcard origin is forbidden for security."""
    with pytest.raises(ValidationError):
        AppSettings(allowed_origins="*")


def test_plain_string_environment_value_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    """A non-JSON ALLOWED_ORIGINS environment value does not crash settings loading."""
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://x.com,http://y.com")
    assert AppSettings().cors_origins == ["http://x.com", "http://y.com"]
