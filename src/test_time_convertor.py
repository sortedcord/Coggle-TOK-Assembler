from datetime import datetime, timezone

from convertors.time import convert_natural_time, _weekday


def _ts(value: datetime) -> int:
    return int(value.timestamp())


def test_relative_days_midnight():
    now = datetime(2024, 3, 15, 10, 30, tzinfo=timezone.utc)
    assert convert_natural_time("yesterday", now) == _ts(
        datetime(2024, 3, 14, tzinfo=timezone.utc)
    )
    assert convert_natural_time("today", now) == _ts(
        datetime(2024, 3, 15, tzinfo=timezone.utc)
    )
    assert convert_natural_time("tomorrow", now) == _ts(
        datetime(2024, 3, 16, tzinfo=timezone.utc)
    )


def test_relative_units_and_numbers():
    now = datetime(2024, 3, 15, 10, 30, tzinfo=timezone.utc)
    assert convert_natural_time("last week", now) == _ts(
        datetime(2024, 3, 8, 10, 30, tzinfo=timezone.utc)
    )
    assert convert_natural_time("next month", now) == _ts(
        datetime(2024, 4, 15, 10, 30, tzinfo=timezone.utc)
    )
    assert convert_natural_time("3 years ago", now) == _ts(
        datetime(2021, 3, 15, 10, 30, tzinfo=timezone.utc)
    )
    assert convert_natural_time("in 4 days", now) == _ts(
        datetime(2024, 3, 19, 10, 30, tzinfo=timezone.utc)
    )
    assert convert_natural_time("5 minutes from now", now) == _ts(
        datetime(2024, 3, 15, 10, 35, tzinfo=timezone.utc)
    )


def test_relative_weekdays():
    now = datetime(2024, 3, 18, 10, 30, tzinfo=timezone.utc)  # Monday
    last_friday = convert_natural_time("last friday", now)
    next_friday = convert_natural_time("next friday", now)
    assert last_friday == _ts(datetime(2024, 3, 15, tzinfo=timezone.utc))
    assert next_friday == _ts(datetime(2024, 3, 22, tzinfo=timezone.utc))
    assert _weekday(datetime.fromtimestamp(last_friday, tz=timezone.utc)) == "friday"
    assert _weekday(datetime.fromtimestamp(next_friday, tz=timezone.utc)) == "friday"


def test_time_of_day_phrases():
    now = datetime(2024, 3, 15, 10, 30, tzinfo=timezone.utc)
    assert convert_natural_time("last night", now) == _ts(
        datetime(2024, 3, 14, 21, 0, tzinfo=timezone.utc)
    )
    assert convert_natural_time("last afternoon", now) == _ts(
        datetime(2024, 3, 14, 15, 0, tzinfo=timezone.utc)
    )
    assert convert_natural_time("next morning", now) == _ts(
        datetime(2024, 3, 16, 9, 0, tzinfo=timezone.utc)
    )
    assert convert_natural_time("yesterday evening", now) == _ts(
        datetime(2024, 3, 14, 19, 0, tzinfo=timezone.utc)
    )


def test_month_day_clamp():
    now = datetime(2024, 1, 31, 10, 30, tzinfo=timezone.utc)
    assert convert_natural_time("next month", now) == _ts(
        datetime(2024, 2, 29, 10, 30, tzinfo=timezone.utc)
    )
