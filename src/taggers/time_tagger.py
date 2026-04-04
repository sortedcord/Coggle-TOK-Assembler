from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable

from dictionary import (
    RELATIVE_DAYS,
    RELATIVE_KEYWORDS,
    TIME_MODIFIERS,
    TIME_OF_DAY,
    TIME_UNITS,
    WEEKDAYS,
)

TIME_LABEL = "TIME"


@dataclass(frozen=True)
class TimeSpan:
    text: str
    start: int
    end: int
    label: str = TIME_LABEL


@dataclass(frozen=True)
class TaggedToken:
    text: str
    start: int
    end: int
    label: str | None = None


def _phrase_pattern(phrases: Iterable[str]) -> str:
    def normalize(phrase: str) -> str:
        return r"\s+".join(re.escape(part) for part in phrase.split())

    normalized = (normalize(phrase) for phrase in phrases)
    sorted_phrases = sorted(normalized, key=len, reverse=True)
    return "(?:" + "|".join(sorted_phrases) + ")"


_TIME_UNITS_PATTERN = _phrase_pattern(TIME_UNITS) + "s?"
_RELATIVE_KEYWORDS_PATTERN = _phrase_pattern(RELATIVE_KEYWORDS)
_RELATIVE_DAYS_PATTERN = _phrase_pattern(RELATIVE_DAYS)
_WEEKDAYS_PATTERN = _phrase_pattern(WEEKDAYS)
_TIME_OF_DAY_PATTERN = _phrase_pattern(TIME_OF_DAY.keys())
_TIME_MODIFIERS_PATTERN = _phrase_pattern(TIME_MODIFIERS)

_TIME_PATTERNS = [
    re.compile(
        r"\b(?:[01]?\d|2[0-3]):[0-5]\d(?:\:[0-5]\d)?\s*(?:am|pm|a\.m\.|p\.m\.)?\b",
        re.IGNORECASE,
    ),
    re.compile(rf"\b\d{{1,2}}\s*(?:am|pm|a\.m\.|p\.m\.)\b", re.IGNORECASE),
    re.compile(
        rf"\b{_RELATIVE_DAYS_PATTERN}\s+{_TIME_OF_DAY_PATTERN}\b", re.IGNORECASE
    ),
    re.compile(
        rf"\b{_RELATIVE_KEYWORDS_PATTERN}\s+{_TIME_OF_DAY_PATTERN}\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b{_RELATIVE_KEYWORDS_PATTERN}\s+{_WEEKDAYS_PATTERN}\b", re.IGNORECASE
    ),
    re.compile(
        rf"\b{_RELATIVE_KEYWORDS_PATTERN}\s+{_TIME_UNITS_PATTERN}\b",
        re.IGNORECASE,
    ),
    re.compile(rf"\b(?:in)\s+\d+\s+{_TIME_UNITS_PATTERN}\b", re.IGNORECASE),
    re.compile(
        rf"\b\d+\s+{_TIME_UNITS_PATTERN}\s+(?:{_TIME_MODIFIERS_PATTERN}|after)\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b\d{{1,2}}\s+(?:in\s+the|at)\s+{_TIME_OF_DAY_PATTERN}\b",
        re.IGNORECASE,
    ),
    re.compile(rf"\b(?:in\s+the|at|this)\s+{_TIME_OF_DAY_PATTERN}\b", re.IGNORECASE),
    re.compile(rf"\b{_RELATIVE_DAYS_PATTERN}\b", re.IGNORECASE),
    re.compile(rf"\b{_TIME_OF_DAY_PATTERN}\b", re.IGNORECASE),
]


def _overlaps(left: TimeSpan, right: TimeSpan) -> bool:
    return left.start < right.end and left.end > right.start


def _dedupe_spans(spans: list[TimeSpan]) -> list[TimeSpan]:
    if not spans:
        return []

    ordered = sorted(spans, key=lambda span: (span.start, -(span.end - span.start)))
    selected: list[TimeSpan] = []
    for span in ordered:
        if any(_overlaps(span, existing) for existing in selected):
            continue
        selected.append(span)
    return sorted(selected, key=lambda span: span.start)


def find_time_spans(query: str) -> list[TimeSpan]:
    if not query or not query.strip():
        return []

    matches: list[TimeSpan] = []
    for pattern in _TIME_PATTERNS:
        for match in pattern.finditer(query):
            start, end = match.span()
            if start == end:
                continue
            matches.append(TimeSpan(text=query[start:end], start=start, end=end))
    return _dedupe_spans(matches)


def tag_time_tokens(query: str) -> list[TaggedToken]:
    if not query or not query.strip():
        return []

    spans = find_time_spans(query)
    tokens: list[TaggedToken] = []
    for match in re.finditer(r"\S+", query):
        start, end = match.span()
        label = (
            TIME_LABEL
            if any(span.start < end and span.end > start for span in spans)
            else None
        )
        tokens.append(
            TaggedToken(text=match.group(0), start=start, end=end, label=label)
        )
    return tokens
