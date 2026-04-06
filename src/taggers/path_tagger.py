from __future__ import annotations

from dataclasses import dataclass
import os
import re
from typing import Iterable

from dictionary import CONTAINER_SYMBOLS
from enums import TokenClass


@dataclass(frozen=True)
class PathSpan:
    text: str
    start: int
    end: int
    label: TokenClass = TokenClass.FILEPATH


@dataclass(frozen=True)
class TaggedToken:
    text: str
    start: int
    end: int
    label: TokenClass | None = None
    confidence: float | None = None


_ABS_PATH_RE = re.compile(r"(?:~/(?:[\w.\-]+/)*[\w.\-]*|/(?:[\w.\-]+/)*[\w.\-]*)")
_REL_PATH_RE = re.compile(r"(?:\.{1,2}/|[\w.\-]+/)(?:[\w.\-]+/)*[\w.\-]*/?")
_SPACED_FWD_RE = re.compile(r"(?:[\w.\-]+\s*/\s*)+[\w.\-]+/?")
_SPACED_BWD_RE = re.compile(r"(?:[\w.\-]+\s*\\\s*)+[\w.\-]+\\?")
_WINDOWS_PATH_RE = re.compile(r"(?:[A-Za-z]:\\(?:[\w.\-]+\\)*[\w.\-]*\\?)")
_FILENAME_EXT_RE = re.compile(r"\b[\w.\-]+\.[A-Za-z0-9]{1,6}\b")
_DOTFILE_RE = re.compile(r"\B\.[A-Za-z0-9][\w.\-]*\b")
_QUOTED_RE = re.compile(r'(["\'])(?P<value>[^"\']+)\1')
_STRIP_RE = re.compile(r'^[\'"`([{<]+|[\'"`)\]}>.,;:!?]+$')
_BARE_WORD_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")


def _normalize_token(token: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", token.lower())


_CONTAINER_SYMBOL_TOKENS: set[str] = set()
_CONTAINER_SYMBOL_PHRASES: list[tuple[str, ...]] = []
for symbol in CONTAINER_SYMBOLS:
    parts = [_normalize_token(part) for part in symbol.split()]
    parts = [part for part in parts if part]
    if not parts:
        continue
    if len(parts) == 1:
        _CONTAINER_SYMBOL_TOKENS.add(parts[0])
    else:
        _CONTAINER_SYMBOL_PHRASES.append(tuple(parts))


def _looks_like_path(text: str) -> bool:
    if not text or not text.strip():
        return False
    stripped = text.strip()
    if stripped.startswith(("~", "/", "./", "../")):
        return True
    if "\\\\" in stripped or "/" in stripped or "\\" in stripped:
        return True
    if re.match(r"^[A-Za-z]:\\", stripped):
        return True
    if _FILENAME_EXT_RE.search(stripped):
        return True
    if _DOTFILE_RE.search(stripped):
        return True
    return False


def _dedupe_spans(spans: list[PathSpan]) -> list[PathSpan]:
    if not spans:
        return []
    ordered = sorted(spans, key=lambda span: (span.start, -(span.end - span.start)))
    selected: list[PathSpan] = []
    for span in ordered:
        if any(span.start < s.end and span.end > s.start for s in selected):
            continue
        selected.append(span)
    return sorted(selected, key=lambda span: span.start)


def _strip_token(token: str) -> str:
    return _STRIP_RE.sub("", token).strip()


def _is_bare_word(token: str) -> bool:
    if not token:
        return False
    if "/" in token or "\\" in token or "." in token:
        return False
    return _BARE_WORD_RE.match(token) is not None


def _container_flags(tokens: list[str]) -> list[bool]:
    normalized = [_normalize_token(token) for token in tokens]
    flags = [token in _CONTAINER_SYMBOL_TOKENS for token in normalized]
    for phrase in _CONTAINER_SYMBOL_PHRASES:
        length = len(phrase)
        for index in range(len(normalized) - length + 1):
            if tuple(normalized[index : index + length]) == phrase:
                for offset in range(length):
                    flags[index + offset] = True
    return flags


def _container_adjacent_confidence(index: int, flags: list[bool]) -> float | None:
    if not flags:
        return None
    prev_flag = flags[index - 1] if index > 0 else False
    next_flag = flags[index + 1] if index + 1 < len(flags) else False
    if prev_flag or next_flag:
        return 0.7
    return None


def find_path_spans(query: str) -> list[PathSpan]:
    if not query or not query.strip():
        return []

    patterns: Iterable[re.Pattern[str]] = (
        _WINDOWS_PATH_RE,
        _ABS_PATH_RE,
        _REL_PATH_RE,
        _SPACED_FWD_RE,
        _SPACED_BWD_RE,
        _FILENAME_EXT_RE,
        _DOTFILE_RE,
    )
    matches: list[PathSpan] = []

    for pattern in patterns:
        for match in pattern.finditer(query):
            start, end = match.span()
            if start == end:
                continue
            matches.append(PathSpan(text=query[start:end], start=start, end=end))

    for match in _QUOTED_RE.finditer(query):
        value = match.group("value")
        if _looks_like_path(value):
            matches.append(
                PathSpan(
                    text=query[match.start() : match.end()],
                    start=match.start(),
                    end=match.end(),
                )
            )

    return _dedupe_spans(matches)


def tag_path_tokens(query: str) -> list[TaggedToken]:
    if not query or not query.strip():
        return []

    spans = find_path_spans(query)
    tokens: list[TaggedToken] = []
    raw_tokens = list(re.finditer(r"\S+", query))
    container_flags = _container_flags([match.group(0) for match in raw_tokens])
    cwd = os.getcwd()
    cwd_entries = list(os.scandir(cwd))
    cwd_names = [entry.name for entry in cwd_entries]
    cwd_names_lower = [name.lower() for name in cwd_names]
    cwd_file_stems = {
        os.path.splitext(entry.name)[0].lower()
        for entry in cwd_entries
        if entry.is_file()
    }

    bare_word_flags = [
        _is_bare_word(_strip_token(match.group(0))) for match in raw_tokens
    ]
    span_flags = [
        any(span.start < match.end() and span.end > match.start() for span in spans)
        for match in raw_tokens
    ]

    for index, match in enumerate(raw_tokens):
        start, end = match.span()
        label = TokenClass.FILEPATH if span_flags[index] else None
        confidence = 1.0 if label is not None else None

        if label is None:
            raw_token = match.group(0)
            stripped = _strip_token(raw_token)
            stripped_lower = stripped.lower()
            normalized = _normalize_token(stripped)
            if (
                stripped
                and _is_bare_word(stripped)
                and normalized not in _CONTAINER_SYMBOL_TOKENS
            ):
                candidate_path = os.path.join(cwd, stripped)
                if os.path.exists(candidate_path):
                    label = TokenClass.FILEPATH
                    confidence = 0.9
                elif stripped_lower in cwd_file_stems:
                    label = TokenClass.FILEPATH
                    confidence = 0.85
                elif any(
                    name.startswith(stripped_lower)
                    for name in cwd_names_lower
                    if stripped_lower
                ):
                    label = TokenClass.FILEPATH
                    confidence = 0.7
                else:
                    proximity = _container_adjacent_confidence(index, container_flags)
                    if proximity is not None:
                        label = TokenClass.FILEPATH
                        confidence = proximity

        if label is None and container_flags[index]:
            prev_bare = bare_word_flags[index - 1] if index > 0 else False
            next_bare = (
                bare_word_flags[index + 1]
                if index + 1 < len(bare_word_flags)
                else False
            )
            prev_is_path = span_flags[index - 1] if index > 0 else False
            next_is_path = (
                span_flags[index + 1]
                if index + 1 < len(span_flags)
                else False
            )
            if prev_bare or next_bare or prev_is_path or next_is_path:
                label = TokenClass.FILEPATH
                confidence = 0.6

        tokens.append(
            TaggedToken(
                text=match.group(0),
                start=start,
                end=end,
                label=label,
                confidence=confidence,
            )
        )
    return tokens
