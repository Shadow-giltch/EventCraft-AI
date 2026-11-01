"""Clock abstraction for deterministic and testable date operations."""

from datetime import date, datetime, timezone
from typing import Protocol

UTC = timezone.utc


class Clock(Protocol):
    """Protocol defining clock interface for time queries."""

    def today(self) -> date:
        """Return the current local or fixed date."""
        ...

    def now_utc(self) -> datetime:
        """Return the current UTC timestamp."""
        ...


class SystemClock:
    """Production clock querying standard system time."""

    def today(self) -> date:
        """Return today's system date."""
        return date.today()

    def now_utc(self) -> datetime:
        """Return current UTC datetime."""
        return datetime.now(UTC)


class FixedClock:
    """Deterministic clock providing a frozen reference date for testing."""

    def __init__(self, current_date: date) -> None:
        """Initialize with a fixed date."""
        self._current_date = current_date

    def today(self) -> date:
        """Return the injected fixed date."""
        return self._current_date

    def now_utc(self) -> datetime:
        """Return injected date positioned at midnight UTC."""
        return datetime(
            self._current_date.year,
            self._current_date.month,
            self._current_date.day,
            tzinfo=UTC,
        )
