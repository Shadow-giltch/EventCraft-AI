"""Validated environment configuration using Pydantic Settings."""

import json
from typing import Any

from pydantic import Field, SecretStr, field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class _LenientDecodeMixin:
    """Fall back to the raw value when a complex env value is not valid JSON."""

    def decode_complex_value(self, field_name: str, field: FieldInfo, value: Any) -> Any:
        """Attempt a JSON decode, returning the raw value if decoding fails."""
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value


class LenientEnvSettingsSource(_LenientDecodeMixin, EnvSettingsSource):
    """Environment source that tolerates plain-string values for complex fields."""


class LenientDotEnvSettingsSource(_LenientDecodeMixin, DotEnvSettingsSource):
    """Dotenv source that tolerates plain-string values for complex fields."""


DEFAULT_ORIGINS: tuple[str, ...] = ("http://localhost:3000", "http://127.0.0.1:3000")


def _split_origins(text: str) -> list[str]:
    """Split a JSON array string or a comma-separated string into raw items."""
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    return text.split(",")


def _normalise_origins(value: Any) -> list[str]:
    """Turn any supported input into a cleaned list of origins."""
    if isinstance(value, str):
        items: list[Any] = _split_origins(value.strip())
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        items = [value]
    return [str(item).strip() for item in items if str(item).strip()]



class AppSettings(BaseSettings):
    """Immutable application settings populated from environment variables."""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Gemini API options (API key is optional; empty string triggers deterministic OfflineClient)
    gemini_api_key: SecretStr = Field(default=SecretStr(""))
    gemini_model: str = Field(default="gemini-3.5-flash-lite")
    gemini_timeout_seconds: float = Field(default=15.0, ge=1.0, le=60.0)
    gemini_max_output_tokens: int = Field(default=1024, ge=128, le=4096)

    # Server options
    host: str = Field(default="0.0.0.0")  # noqa: S104 # nosec B104
    port: int = Field(default=3000, ge=1024, le=65535)
    environment: str = Field(default="production")
    allowed_origins: list[str] | str = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    trust_proxy: bool = Field(default=False)

    # Security & Capacity limits
    body_limit_bytes: int = Field(default=32768, ge=1024, le=1048576)
    rate_limit_per_minute: int = Field(default=60, ge=5, le=1000)
    max_concurrent_llm_calls: int = Field(default=10, ge=1, le=50)

    # In-memory cache options
    cache_ttl_seconds: float = Field(default=3600.0, ge=60.0, le=86400.0)
    cache_max_size: int = Field(default=1000, ge=10, le=100000)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Use lenient sources to avoid JSONDecodeError on plain string env vars."""
        return (
            init_settings,
            LenientEnvSettingsSource(settings_cls),
            LenientDotEnvSettingsSource(settings_cls),
            file_secret_settings,
        )

    @property
    def cors_origins(self) -> list[str]:
        """Return allowed origins guaranteed to be a list of strings."""
        if isinstance(self.allowed_origins, list):
            return self.allowed_origins
        return [str(self.allowed_origins)]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Any) -> list[str]:
            """Parse allowed origins from JSON string, comma-separated string, or list."""
            origins = _normalise_origins(value) if value else []
            if "*" in origins:
                 raise ValueError("Wildcard '*' origin is forbidden for security.")
            return origins or list(DEFAULT_ORIGINS)
