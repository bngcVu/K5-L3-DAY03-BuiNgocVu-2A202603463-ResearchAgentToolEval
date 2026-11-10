"""Heuristic graders for the FINAL answer of an agent run (pure functions, no network).

`run_eval.py` grades the first model step only (which tool, which args). It cannot see what the
user finally reads. These checks grade that text:

- language_ok      : the answer is written in the user's language (Vietnamese), not English
- grounded_ok      : every URL in the answer really came from a tool result (no invented links)
- no_duplicates_ok : no URL is listed twice
- fresh_ok         : every cited news item with a publish date is inside the requested window
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

URL_RE = re.compile(r"https?://[^\s\)\]>\"']+")
WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
# Letters that only exist in Vietnamese (base letters with their own form + every tone-marked vowel).
VI_CHARS = set("ăâđêôơưÀÁẢÃẠẦẤẨẪẬẰẮẲẴẶÈÉẺẼẸỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌỒỐỔỖỘỜỚỞỠỢÙÚỦŨỤỪỨỬỮỰỲÝỶỸỴ"
               "àáảãạầấẩẫậằắẳẵặèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ"
               "ĂÂĐÊÔƠƯ")
# Distinctive English function words (none is a common Vietnamese word).
EN_STOPWORDS = {
    "the", "and", "of", "is", "are", "here", "some", "latest", "feel", "free", "if", "you", "your", "need",
    "more", "about", "with", "for", "from", "that", "this", "has", "have", "will", "was", "were", "which",
    "please", "let", "know", "or", "also", "been", "their", "there", "these", "those", "would", "could",
    "can", "may", "into", "after", "before", "today", "details", "information", "specific",
    "articles", "highlights", "source",
}
WINDOW_DAYS = {"day": 2.0, "week": 8.0, "month": 32.0, "year": 370.0}


def _prose(text: str) -> str:
    """Drop URLs and markdown link targets so domains and links do not count as words."""
    text = URL_RE.sub(" ", text or "")
    return re.sub(r"[*_`#>\[\]()]", " ", text)


def english_ratio(text: str) -> float:
    words = [w.lower() for w in WORD_RE.findall(_prose(text))]
    if not words:
        return 0.0
    return sum(1 for w in words if w in EN_STOPWORDS) / len(words)


def vietnamese_char_ratio(text: str) -> float:
    letters = [c for c in _prose(text) if c.isalpha()]
    if not letters:
        return 0.0
    return sum(1 for c in letters if c in VI_CHARS) / len(letters)


def is_vietnamese(text: str, *, max_english_ratio: float = 0.04, min_vi_char_ratio: float = 0.04) -> bool:
    """True when the prose is Vietnamese. Foreign headlines/names are tolerated, an English reply is not."""
    if not (text or "").strip():
        return False
    return english_ratio(text) <= max_english_ratio and vietnamese_char_ratio(text) >= min_vi_char_ratio


def extract_urls(text: str) -> list[str]:
    return [u.rstrip(".,;:!?") for u in URL_RE.findall(text or "")]


def _norm_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    return re.sub(r"^https?://(www\.)?", "", url).lower()


def _tool_items(tool_events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Map normalized URL -> item for every item any tool returned."""
    seen: dict[str, dict[str, Any]] = {}
    for event in tool_events or []:
        result = event.get("result") if isinstance(event, dict) else None
        if not isinstance(result, dict):
            continue
        for item in result.get("items") or result.get("results") or []:
            if isinstance(item, dict) and item.get("url"):
                seen[_norm_url(item["url"])] = item
    return seen


def _urls_in_tool_results(tool_events: list[dict[str, Any]]) -> set[str]:
    """Every URL that appears ANYWHERE in the tool results (item urls and links inside tweet/snippet text)."""
    blob = json.dumps([e.get("result") for e in tool_events or [] if isinstance(e, dict)], ensure_ascii=False, default=str)
    return {_norm_url(u) for u in extract_urls(blob)}


def parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = parsedate_to_datetime(str(value))
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError:
            return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def grade_answer(
    final_text: str,
    tool_events: list[dict[str, Any]],
    *,
    language: str | None = "vi",
    timeframe: str | None = None,
    requires_sources: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return {check_name: bool|None, "failures": [...]}; None means the check did not apply."""
    now = now or datetime.now(timezone.utc)
    urls = extract_urls(final_text)
    known = _tool_items(tool_events)
    known_urls = _urls_in_tool_results(tool_events)
    failures: list[str] = []

    language_ok: bool | None = None
    if language == "vi":
        language_ok = is_vietnamese(final_text)
        if not language_ok:
            failures.append(f"answer is not Vietnamese (english_ratio={english_ratio(final_text):.2f})")

    grounded_ok: bool | None = None
    if urls:
        invented = [u for u in urls if _norm_url(u) not in known_urls]
        grounded_ok = not invented
        if invented:
            failures.append(f"URL not returned by any tool: {invented[0]}")

    no_duplicates_ok: bool | None = None
    if urls:
        normalized = [_norm_url(u) for u in urls]
        no_duplicates_ok = len(normalized) == len(set(normalized))
        if not no_duplicates_ok:
            failures.append("a URL is listed more than once")

    fresh_ok: bool | None = None
    if timeframe in WINDOW_DAYS:
        limit = WINDOW_DAYS[timeframe]
        dated = []
        for u in urls:
            item = known.get(_norm_url(u))
            published = parse_date(item.get("published_date")) if item else None
            if published:
                dated.append((u, (now - published).total_seconds() / 86400))
        if dated:
            stale = [u for u, age in dated if age > limit]
            fresh_ok = not stale
            if stale:
                failures.append(f"cited item older than {timeframe} window: {stale[0]}")

    sources_ok: bool | None = None
    if requires_sources:
        sources_ok = bool(urls)
        if not sources_ok:
            failures.append("answer cites no source URL")

    return {
        "language_ok": language_ok,
        "grounded_ok": grounded_ok,
        "no_duplicates_ok": no_duplicates_ok,
        "fresh_ok": fresh_ok,
        "sources_ok": sources_ok,
        "failures": failures,
    }


def passed(grade: dict[str, Any]) -> bool:
    return not grade["failures"]
