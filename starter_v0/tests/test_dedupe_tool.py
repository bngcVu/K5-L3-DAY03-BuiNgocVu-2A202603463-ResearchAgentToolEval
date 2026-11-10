"""Unit tests for the team tool `dedupe` (pure local, no network)."""
from __future__ import annotations

import pytest

from tools import TOOL_FUNCTIONS

dedupe = TOOL_FUNCTIONS["dedupe"]


def test_dedupe_removes_same_url_ignoring_www_tracking_and_trailing_slash() -> None:
    items = [
        {"title": "GPT-5 ra mắt", "url": "https://openai.com/blog/gpt-5"},
        {"title": "GPT-5 launch", "url": "https://www.openai.com/blog/gpt-5/?utm_source=x&utm_medium=y#top"},
        {"title": "Tin khác", "url": "https://example.com/a"},
    ]
    result = dedupe(items=items)

    assert result["item_count"] == 2
    assert result["removed_count"] == 1
    assert [i["url"] for i in result["items"]] == ["https://openai.com/blog/gpt-5", "https://example.com/a"]
    assert result["duplicates"][0]["index"] == 1 and result["duplicates"][0]["duplicate_of"] == 0


def test_dedupe_keeps_distinct_query_params_that_change_the_page() -> None:
    items = [{"url": "https://example.com/watch?v=1"}, {"url": "https://example.com/watch?v=2"}]
    assert dedupe(items=items)["removed_count"] == 0


def test_dedupe_by_title_ignores_case_accents_and_punctuation() -> None:
    items = [
        {"title": "Tin tức AI hôm nay!", "url": "https://a.com/1"},
        {"title": "tin tuc ai hom nay", "url": "https://b.com/2"},
    ]
    by_title = dedupe(items=items, by="title")
    assert by_title["item_count"] == 1 and by_title["items"][0]["url"] == "https://a.com/1"
    # Different URLs are not duplicates when comparing by url.
    assert dedupe(items=items, by="url")["item_count"] == 2


def test_dedupe_keeps_first_occurrence_and_order() -> None:
    items = [{"url": "https://x.com/3"}, {"url": "https://x.com/1"}, {"url": "https://x.com/3"}, {"url": "https://x.com/2"}]
    result = dedupe(items=items)
    assert [i["url"] for i in result["items"]] == ["https://x.com/3", "https://x.com/1", "https://x.com/2"]


def test_dedupe_never_drops_items_that_have_no_url_or_title() -> None:
    items = [{"summary": "a"}, {"summary": "b"}, {}]
    result = dedupe(items=items)
    assert result["item_count"] == 3 and result["removed_count"] == 0


def test_dedupe_falls_back_to_title_when_url_missing() -> None:
    items = [{"title": "Cùng một tin"}, {"title": "cung mot tin"}]
    assert dedupe(items=items, by="url")["item_count"] == 1


def test_dedupe_limit_truncates_after_dedupe() -> None:
    items = [{"url": f"https://x.com/{i % 4}"} for i in range(8)]  # 4 unique
    result = dedupe(items=items, limit=3)
    assert result["item_count"] == 3 and result["removed_count"] == 4


def test_dedupe_accepts_numeric_string_limit() -> None:
    items = [{"url": f"https://x.com/{i}"} for i in range(5)]
    assert dedupe(items=items, limit="2")["item_count"] == 2


def test_dedupe_empty_or_none_items_returns_empty_result() -> None:
    for value in ([], None):
        result = dedupe(items=value)
        assert result["items"] == [] and result["item_count"] == 0 and "error" not in result


@pytest.mark.parametrize(
    "kwargs",
    [
        {"items": "not a list"},
        {"items": [{"url": "https://x.com"}], "by": "author"},
        {"items": [{"url": "https://x.com"}], "limit": -1},
        {"items": [{"url": "https://x.com"}], "limit": "abc"},
    ],
)
def test_dedupe_bad_input_returns_error_dict_instead_of_raising(kwargs) -> None:
    result = dedupe(**kwargs)
    assert result["tool"] == "dedupe"
    assert result["error"] in {"TypeError", "ValueError"}
    assert result["message"]


def test_dedupe_skips_non_dict_items_and_reports_them() -> None:
    result = dedupe(items=[{"url": "https://x.com/1"}, "oops", 5, None])
    assert result["item_count"] == 1 and result["skipped_invalid"] == 3
