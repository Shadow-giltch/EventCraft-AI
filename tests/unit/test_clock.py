from datetime import date

from eventcraft.domain.clock import UTC, FixedClock, SystemClock


def test_fixed_clock_returns_injected_date():
    target = date(2026, 12, 25)
    clock = FixedClock(target)
    assert clock.today() == target
    utc_dt = clock.now_utc()
    assert utc_dt.date() == target
    assert utc_dt.tzinfo == UTC


def test_system_clock_returns_current_date():
    clock = SystemClock()
    assert isinstance(clock.today(), date)
    utc_now = clock.now_utc()
    assert utc_now.tzinfo == UTC
