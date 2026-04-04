from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class MimeTypeStore:
    mimetype_to_extensions: dict[str, tuple[str, ...]]
    extension_to_mimetypes: dict[str, tuple[str, ...]]
    categories: tuple[str, ...]
    search_terms: tuple[str, ...]
    search_term_to_result: dict[str, str]


_MIME_TYPES_DIR = Path(__file__).resolve().parents[1]
_MIME_TYPES_GLOB = "*.types"
_MIME_TYPE_STORE: MimeTypeStore | None = None


def normalize_mime_token(token: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", token.lower())


def _resolve_mime_type_paths(
    mime_types_path: Path | Iterable[Path] | None,
) -> tuple[Path, ...]:
    if mime_types_path is None:
        paths = tuple(
            sorted(_MIME_TYPES_DIR.glob(_MIME_TYPES_GLOB), key=lambda p: p.name)
        )
        if not paths:
            raise FileNotFoundError(f"no mime types files found in: {_MIME_TYPES_DIR}")
        return paths

    if isinstance(mime_types_path, Path):
        paths: Iterable[Path] = (mime_types_path,)
    else:
        paths = mime_types_path

    expanded_paths: list[Path] = []
    for path in paths:
        if path.is_dir():
            dir_paths = sorted(path.glob(_MIME_TYPES_GLOB), key=lambda p: p.name)
            if not dir_paths:
                raise FileNotFoundError(f"no mime types files found in: {path}")
            expanded_paths.extend(dir_paths)
        else:
            expanded_paths.append(path)

    if not expanded_paths:
        raise FileNotFoundError("no mime types files provided")

    missing = [path for path in expanded_paths if not path.exists()]
    if missing:
        missing_display = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"mime types file not found: {missing_display}")

    return tuple(expanded_paths)


def build_mime_type_store(
    mime_types_path: Path | Iterable[Path] | None = None,
) -> MimeTypeStore:
    paths = _resolve_mime_type_paths(mime_types_path)

    mimetype_to_extensions: dict[str, list[str]] = {}
    extension_to_mimetypes: dict[str, set[str]] = {}
    categories: set[str] = set()

    for path in paths:
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            if not parts:
                continue
            mimetype = parts[0].lower()
            extensions = [ext.lower().lstrip(".") for ext in parts[1:]]
            mimetype_to_extensions.setdefault(mimetype, []).extend(extensions)
            category = mimetype.split("/", 1)[0]
            categories.add(category)
            for ext in extensions:
                extension_to_mimetypes.setdefault(ext, set()).add(mimetype)

    mimetype_to_extensions_final = {
        mimetype: tuple(extensions)
        for mimetype, extensions in mimetype_to_extensions.items()
    }
    extension_to_mimetypes_final = {
        ext: tuple(sorted(mimetypes))
        for ext, mimetypes in extension_to_mimetypes.items()
    }
    categories_final = tuple(sorted(categories))

    search_term_to_result: dict[str, str] = {}

    def add_search_term(term: str, result: str) -> None:
        normalized = normalize_mime_token(term)
        if not normalized:
            return
        search_term_to_result.setdefault(normalized, result)

    for category in categories_final:
        add_search_term(category, category)

    for mimetype in sorted(mimetype_to_extensions_final):
        add_search_term(mimetype, mimetype)
        subtype = mimetype.split("/", 1)[1]
        add_search_term(subtype, mimetype)

    for extension, mimetypes in sorted(extension_to_mimetypes_final.items()):
        add_search_term(extension, mimetypes[0])

    search_terms = tuple(search_term_to_result.keys())

    return MimeTypeStore(
        mimetype_to_extensions=mimetype_to_extensions_final,
        extension_to_mimetypes=extension_to_mimetypes_final,
        categories=categories_final,
        search_terms=search_terms,
        search_term_to_result=search_term_to_result,
    )


def get_mime_type_store() -> MimeTypeStore:
    global _MIME_TYPE_STORE
    if _MIME_TYPE_STORE is None:
        _MIME_TYPE_STORE = build_mime_type_store()
    return _MIME_TYPE_STORE


def _extensions_for_category(category: str, store: MimeTypeStore) -> tuple[str, ...]:
    extensions: set[str] = set()
    for mimetype, mimetype_extensions in store.mimetype_to_extensions.items():
        if mimetype.startswith(f"{category}/"):
            extensions.update(mimetype_extensions)
    return tuple(sorted(extensions))


def resolve_mime_extensions(
    mimetype: str,
    store: MimeTypeStore | None = None,
) -> tuple[str, ...] | None:
    if not mimetype or not mimetype.strip():
        return None

    store = store or get_mime_type_store()
    token = mimetype.strip().lower()

    if token in store.mimetype_to_extensions:
        return store.mimetype_to_extensions[token]

    if token in store.categories:
        return _extensions_for_category(token, store)

    return None


MIME_TYPE_STORE = get_mime_type_store()
