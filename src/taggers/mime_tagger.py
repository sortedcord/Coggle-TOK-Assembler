from __future__ import annotations

from dataclasses import dataclass
import re

from rapidfuzz import fuzz, process

from dictionary import MIME_META_TERMS, MIME_NEIGHBOR_TOKENS
from processors.mime_processor import (
    MimeTypeStore,
    get_mime_type_store,
    normalize_mime_token,
)

MIME_LABEL = "MIME"


@dataclass(frozen=True)
class TaggedToken:
    text: str
    start: int
    end: int
    label: str | None = None
    match: str | None = None


def fuzzy_match_mimetype_category(
    token: str,
    store: MimeTypeStore | None = None,
    *,
    cutoff: float = 90.0,
) -> str | None:
    if not token or not token.strip():
        return None

    store = store or get_mime_type_store()
    token = token.strip().lower()

    if token in store.categories:
        return token

    fallback_category = None
    if "/" in token:
        category = token.split("/", 1)[0]
        if category in store.categories:
            fallback_category = category

    if token in store.mimetype_to_extensions:
        return token

    extension = token.lstrip(".")
    if extension in store.extension_to_mimetypes:
        return store.extension_to_mimetypes[extension][0]

    normalized = normalize_mime_token(token)
    if not normalized:
        return None

    if normalized in store.search_term_to_result:
        return store.search_term_to_result[normalized]

    if len(normalized) < 4:
        return fallback_category

    score_cutoff = cutoff * 100 if cutoff <= 1.0 else cutoff
    match = process.extractOne(
        normalized,
        store.search_terms,
        scorer=fuzz.QRatio,
        score_cutoff=score_cutoff,
        processor=None,
    )
    if match:
        return store.search_term_to_result[match[0]]
    return fallback_category


def tag_mime_tokens(
    query: str,
    store: MimeTypeStore | None = None,
    *,
    cutoff: float = 90.0,
) -> list[TaggedToken]:
    if not query or not query.strip():
        return []

    store = store or get_mime_type_store()
    tokens: list[TaggedToken] = []
    raw_tokens = list(re.finditer(r"\S+", query))
    normalized_tokens = [normalize_mime_token(match.group(0)) for match in raw_tokens]
    meta_terms = {normalize_mime_token(term) for term in MIME_META_TERMS}
    neighbor_terms = {normalize_mime_token(term) for term in MIME_NEIGHBOR_TOKENS}

    matched_tokens: list[TaggedToken] = []
    for match, normalized in zip(raw_tokens, normalized_tokens, strict=True):
        token = match.group(0)
        start, end = match.span()
        matched = fuzzy_match_mimetype_category(token, store, cutoff=cutoff)
        if matched is None and normalized in meta_terms:
            matched = normalized
        label = MIME_LABEL if matched is not None else None
        matched_tokens.append(
            TaggedToken(
                text=token,
                start=start,
                end=end,
                label=label,
                match=matched,
            )
        )

    tokens = list(matched_tokens)
    for index, tagged in enumerate(matched_tokens):
        if tagged.label is None:
            continue
        for neighbor_index in (index - 1, index + 1):
            if neighbor_index < 0 or neighbor_index >= len(matched_tokens):
                continue
            neighbor = matched_tokens[neighbor_index]
            if neighbor.label is not None:
                continue
            normalized_neighbor = normalized_tokens[neighbor_index]
            if normalized_neighbor in neighbor_terms:
                tokens[neighbor_index] = TaggedToken(
                    text=neighbor.text,
                    start=neighbor.start,
                    end=neighbor.end,
                    label=MIME_LABEL,
                    match=neighbor.match,
                )

    return tokens
