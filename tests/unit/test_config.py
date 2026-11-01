import pytest
from pydantic import SecretStr, ValidationError

from eventcraft.config import AppSettings


def test_config_defaults(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # no .env in this folder, so real defaults apply
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    settings = AppSettings(port=3000)
    assert settings.port == 3000
    assert settings.gemini_model == "gemini-3.5-flash-lite"
    # keep your other existing assert lines below, unchanged


def test_config_wildcard_origin_rejected():
    with pytest.raises(ValidationError, match="Wildcard"):
        AppSettings(allowed_origins=["*"])


def test_config_origin_json_parsing():
    settings = AppSettings(allowed_origins='["http://example.com"]')
    assert settings.cors_origins == ["http://example.com"]


def test_config_origin_plain_string_parsing():
    settings = AppSettings(allowed_origins="http://example.com")
    assert settings.cors_origins == ["http://example.com"]


def test_config_origin_comma_separated_parsing():
    settings = AppSettings(allowed_origins="http://a.com, http://b.com")
    assert settings.cors_origins == ["http://a.com", "http://b.com"]


def test_config_origin_empty_string_falls_back():
    settings = AppSettings(allowed_origins="")
    assert len(settings.cors_origins) >= 1


def test_config_secret_not_revealed_in_repr():
    settings = AppSettings(gemini_api_key=SecretStr("super-secret-key-xyz"))
    repr_str = repr(settings)
    assert "super-secret-key-xyz" not in repr_str
