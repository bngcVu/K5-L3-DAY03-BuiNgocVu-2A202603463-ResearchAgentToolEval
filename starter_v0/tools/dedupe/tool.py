from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse

from tools._shared import err, fold_text

_TRACKING_PARAMS = {"fbclid", "gclid", "ref", "ref_src", "igshid", "mc_cid", "mc_eid"}
_BY_VALUES = {"url", "title"}


def _norm_url(url: str) -> str:
    """Canonical form of a URL so tracking noise does not hide a duplicate."""
    url = (url or "").strip()
    if not url:
        return ""
    parsed = urlparse(url if "://" in url else f"//{url}")
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in _TRACKING_PARAMS
    ]
    path = parsed.path.rstrip("/")
    return f"{host}{path}" + (f"?{urlencode(sorted(query))}" if query else "")


def _norm_title(title: str) -> str:
    """Lowercase, strip accents and punctuation so 'GPT-5 Launch!' == 'gpt 5 launch'."""
    return " ".join(re.findall(r"[a-z0-9]+", fold_text(title or "")))


def _key_for(item: dict[str, Any], by: str) -> str:
    primary = _norm_url(str(item.get("url") or "")) if by == "url" else _norm_title(str(item.get("title") or ""))
    if primary:
        return f"{by}:{primary}"
    # The chosen field is missing: fall back to the other one rather than dropping the item.
    fallback_by = "title" if by == "url" else "url"
    fallback = (
        _norm_title(str(item.get("title") or ""))
        if fallback_by == "title"
        else _norm_url(str(item.get("url") or ""))
    )
    return f"{fallback_by}:{fallback}" if fallback else ""


def dedupe_items(items: list[dict[str, Any]] | None = None, by: str = "url", limit: int = 0) -> dict[str, Any]:
    """Remove duplicate items (keeps the first occurrence, preserves order)."""
    try:
        if items is None:
            items = []
        if not isinstance(items, list):
            raise TypeError("items must be a list of objects with 'url' and/or 'title'")
        if by not in _BY_VALUES:
            raise ValueError(f"by must be one of {sorted(_BY_VALUES)}, got {by!r}")
        limit = int(limit or 0)
        if limit < 0:
            raise ValueError("limit must be >= 0 (0 means no limit)")
    except (TypeError, ValueError) as exc:
        return err("dedupe", exc)

    seen: dict[str, int] = {}
    kept: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    skipped_invalid = 0
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            skipped_invalid += 1
            continue
        key = _key_for(item, by)
        if key and key in seen:
            duplicates.append({
                "index": index,
                "duplicate_of": seen[key],
                "title": item.get("title", ""),
                "url": item.get("url", ""),
            })
            continue
        if key:
            seen[key] = index
        kept.append(item)

    if limit:
        kept = kept[:limit]
    return {
        "tool": "dedupe",
        "by": by,
        "items": kept,
        "item_count": len(kept),
        "removed_count": len(duplicates),
        "skipped_invalid": skipped_invalid,
        "duplicates": duplicates,
    }
