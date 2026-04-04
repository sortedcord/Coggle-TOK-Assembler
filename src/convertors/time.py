from __future__ import annotations

from datetime import datetime, timedelta, timezone
import calendar
import re

from dictionary import (
    RELATIVE_DAYS,
    RELATIVE_KEYWORDS,
    TIME_MODIFIERS,
    TIME_OF_DAY,
    TIME_UNITS,
    WEEKDAYS,
)


def _weekday(value: datetime) -> str:
    return value.strftime("%A").lower()


def _normalize_phrase(phrase: str) -> str:
    return re.sub(r"\s+", " ", phrase.strip().lower())


def _ensure_timezone(now: datetime) -> datetime:
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now


def _normalize_unit(unit: str) -> str:
    unit = unit.lower()
    if unit.endswith("s"):
        unit = unit[:-1]
    return unit


def _shift_month(now: datetime, months: int) -> datetime:
    month_index = (now.month - 1) + months
    year = now.year + (month_index // 12)
    month = (month_index % 12) + 1
    day = min(now.day, calendar.monthrange(year, month)[1])
    return now.replace(year=year, month=month, day=day)


def _shift_year(now: datetime, years: int) -> datetime:
    year = now.year + years
    day = min(now.day, calendar.monthrange(year, now.month)[1])
    return now.replace(year=year, day=day)


def _shift_unit(now: datetime, unit: str, count: int) -> datetime | None:
    if unit == "second":
        return now + timedelta(seconds=count)
    if unit == "minute":
        return now + timedelta(minutes=count)
    if unit == "hour":
        return now + timedelta(hours=count)
    if unit == "day":
        return now + timedelta(days=count)
    if unit == "week":
        return now + timedelta(weeks=count)
    if unit == "month":
        return _shift_month(now, count)
    if unit == "year":
        return _shift_year(now, count)
    return None


def _shift_weekday(now: datetime, target_weekday: int, direction: int) -> datetime:
    current = now.weekday()
    if direction < 0:
        delta = (current - target_weekday) % 7
        if delta == 0:
            delta = 7
        result = now - timedelta(days=delta)
    elif direction > 0:
        delta = (target_weekday - current) % 7
        if delta == 0:
            delta = 7
        result = now + timedelta(days=delta)
    else:
        delta = (target_weekday - current) % 7
        result = now + timedelta(days=delta)
    return result.replace(hour=0, minute=0, second=0, microsecond=0)


def _shift_time_of_day(now: datetime, hour: int, direction: int) -> datetime:
    base = now + timedelta(days=direction)
    return base.replace(hour=hour, minute=0, second=0, microsecond=0)


def convert_natural_time(phrase: str, now: datetime | None = None) -> int | None:
    if not phrase or not phrase.strip():
        return None

    now = _ensure_timezone(now or datetime.now(timezone.utc))
    text = _normalize_phrase(phrase)

    if text in RELATIVE_DAYS:
        delta = {"yesterday": -1, "today": 0, "tomorrow": 1}[text]
        result = now + timedelta(days=delta)
        return int(
            result.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        )

    tokens = text.split()

    if tokens and tokens[0] in RELATIVE_DAYS and len(tokens) >= 2:
        time_of_day = tokens[1]
        if time_of_day in TIME_OF_DAY:
            delta = {"yesterday": -1, "today": 0, "tomorrow": 1}[tokens[0]]
            result = now + timedelta(days=delta)
            return int(
                result.replace(
                    hour=TIME_OF_DAY[time_of_day],
                    minute=0,
                    second=0,
                    microsecond=0,
                ).timestamp()
            )

    if tokens and tokens[0] in RELATIVE_KEYWORDS and len(tokens) >= 2:
        direction = {"last": -1, "next": 1, "this": 0}[tokens[0]]
        target = tokens[1]
        if target in TIME_UNITS:
            shifted = _shift_unit(now, target, direction)
            if shifted is None:
                return None
            return int(shifted.timestamp())
        if target in WEEKDAYS:
            weekday_index = WEEKDAYS.index(target)
            return int(_shift_weekday(now, weekday_index, direction).timestamp())
        if target in TIME_OF_DAY:
            return int(
                _shift_time_of_day(now, TIME_OF_DAY[target], direction).timestamp()
            )

    if text.startswith("in "):
        tokens = text.split()
        if len(tokens) == 3 and tokens[1].isdigit():
            unit = _normalize_unit(tokens[2])
            if unit in TIME_UNITS:
                shifted = _shift_unit(now, unit, int(tokens[1]))
                if shifted is None:
                    return None
                return int(shifted.timestamp())

    if tokens and tokens[0].isdigit() and len(tokens) >= 3:
        count = int(tokens[0])
        unit = _normalize_unit(tokens[1])
        modifier = " ".join(tokens[2:])
        if unit in TIME_UNITS and modifier in TIME_MODIFIERS + ["after"]:
            direction = 1 if modifier in {"from now", "after"} else -1
            shifted = _shift_unit(now, unit, count * direction)
            if shifted is None:
                return None
            return int(shifted.timestamp())

    return None
