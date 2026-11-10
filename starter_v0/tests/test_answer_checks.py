"""Tests for the answer-level grader and the multi-round runner (offline, fake provider)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

import answer_checks as ac
import run_answer_eval
from conftest import FakeResponse
from providers.base import ModelResponse, ToolCall

NOW = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)

VI_ANSWER = (
    "Dưới đây là một số tin nổi bật hôm nay:\n\n"
    "1. Bộ trưởng Hegseth đối mặt sức ép luận tội - Hạ viện Mỹ chuẩn bị xem xét các cáo buộc. "
    "(vtcnews.vn, 10/11) https://vtcnews.vn/a\n\n"
    "Bạn có muốn mình thu hẹp theo khu vực hoặc lĩnh vực không?"
)
EN_ANSWER = (
    "Here are the latest news highlights for today:\n\n"
    "The U.S. House is preparing to consider impeachment charges. Read more (Source: vtcnews.vn)\n\n"
    "Feel free to check the links for more detailed information!"
)
# v1 sample from problem_ans.md: Vietnamese headlines but an English frame around them.
MIXED_ANSWER = (
    "Here are some of the latest news articles from today:\n\n"
    "Tin tức quốc tế ngày 10.11: Tổng thống Trump ra một loạt tuyên bố quan trọng (Source: thanhnien.vn)\n\n"
    "Thủ tướng Israel kêu gọi thành lập một chính phủ đoàn kết.\n\n"
    "Nếu bạn cần thêm thông tin hoặc muốn tìm hiểu về một chủ đề cụ thể nào khác, hãy cho tôi biết!"
)


def _event(url: str, published: datetime | None) -> dict:
    item = {"title": "t", "url": url, "source": "x", "summary": "s", "score": 0.5}
    if published:
        item["published_date"] = published.strftime("%a, %d %b %Y %H:%M:%S GMT")
    return {"tool": "web_search", "args": {}, "result": {"items": [item]}}


# ---------------- language ----------------

def test_vietnamese_answer_is_recognised() -> None:
    assert ac.is_vietnamese(VI_ANSWER)


@pytest.mark.parametrize("text", [EN_ANSWER, MIXED_ANSWER, ""])
def test_english_or_mixed_reply_to_a_vietnamese_user_is_rejected(text) -> None:
    assert not ac.is_vietnamese(text)


def test_foreign_proper_nouns_and_urls_do_not_make_a_vietnamese_answer_english() -> None:
    text = "Theo MIT News, nhóm nghiên cứu nhận tài trợ phát triển robot. Nguồn: https://news.mit.edu/the-news-of-the-day"
    assert ac.is_vietnamese(text)


# ---------------- grounding / duplicates / freshness ----------------

def test_invented_url_is_flagged() -> None:
    grade = ac.grade_answer(VI_ANSWER, [_event("https://other.vn/b", NOW)], language="vi", now=NOW)

    assert grade["grounded_ok"] is False
    assert any("not returned by any tool" in f for f in grade["failures"])


def test_url_from_tool_result_is_accepted_even_with_www_or_trailing_slash() -> None:
    grade = ac.grade_answer(VI_ANSWER, [_event("https://www.vtcnews.vn/a/", NOW)], language="vi", now=NOW)

    assert grade["grounded_ok"] is True


def test_duplicate_url_is_flagged() -> None:
    text = "Tin A https://vtcnews.vn/a\nTin A lần nữa https://vtcnews.vn/a/"
    grade = ac.grade_answer(text, [_event("https://vtcnews.vn/a", NOW)], language="vi", now=NOW)

    assert grade["no_duplicates_ok"] is False


def test_stale_item_is_flagged_for_a_day_window_and_fresh_item_passes() -> None:
    stale = ac.grade_answer(VI_ANSWER, [_event("https://vtcnews.vn/a", NOW - timedelta(days=5))],
                            language="vi", timeframe="day", now=NOW)
    fresh = ac.grade_answer(VI_ANSWER, [_event("https://vtcnews.vn/a", NOW - timedelta(hours=6))],
                            language="vi", timeframe="day", now=NOW)

    assert stale["fresh_ok"] is False and any("older than day" in f for f in stale["failures"])
    assert fresh["fresh_ok"] is True


def test_item_without_publish_date_does_not_fail_freshness() -> None:
    grade = ac.grade_answer(VI_ANSWER, [_event("https://vtcnews.vn/a", None)], language="vi", timeframe="day", now=NOW)

    assert grade["fresh_ok"] is None


def test_requires_sources_fails_when_no_url_is_cited() -> None:
    grade = ac.grade_answer("Hôm nay không có tin gì đặc biệt.", [], language="vi", requires_sources=True, now=NOW)

    assert grade["sources_ok"] is False


# ---------------- multi-round runner with a fake provider ----------------

class ScriptedProvider:
    default_model = "fake"

    def __init__(self, responses: list[ModelResponse]) -> None:
        self.responses = list(responses)
        self.seen: list[list[dict]] = []

    def complete(self, messages, tools=None, *, model=None, temperature=0.0, tool_choice=None) -> ModelResponse:
        self.seen.append(messages)
        return self.responses.pop(0)


def _lookup_payload() -> dict:
    published = (datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%a, %d %b %Y %H:%M:%S GMT")
    return {"results": [{"title": "Tin A", "url": "https://vtcnews.vn/a", "content": "nội dung", "score": 0.6,
                         "published_date": published}]}


def test_runner_answers_a_clarifying_question_then_grades_the_final_answer(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    fake_http(FakeResponse(_lookup_payload()))
    provider = ScriptedProvider([
        ModelResponse(text=None, tool_calls=[ToolCall("clarify", {"question": "Bạn muốn tin nào?", "response_type": "choice",
                                                                  "options": ["Tin Việt Nam", "Tin thế giới"]})]),
        ModelResponse(text=None, tool_calls=[ToolCall("lookup", {"query": "tin tức nổi bật", "topic": "news", "timeframe": "day"})]),
        ModelResponse(text=VI_ANSWER, tool_calls=[]),
    ])
    case = {"id": "T", "turns": ["tin tức hôm nay"], "clarify_reply": "Tin Việt Nam",
            "expect": {"language": "vi", "requires_sources": True}}

    result = run_answer_eval.run_case(provider, case, "system", [], None)

    assert result["asked_clarify"] is True
    assert result["answered"] is True
    assert result["passed"] is True, result["grade"]["failures"]
    assert result["grade"]["fresh_ok"] is True
    # The clarify reply reached the model as the next user message.
    assert {"role": "user", "content": "Tin Việt Nam"} in provider.seen[1]


def test_runner_fails_an_english_final_answer(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    fake_http(FakeResponse(_lookup_payload()))
    provider = ScriptedProvider([
        ModelResponse(text=None, tool_calls=[ToolCall("lookup", {"query": "tin tức", "topic": "news", "timeframe": "day"})]),
        ModelResponse(text=EN_ANSWER, tool_calls=[]),
    ])
    case = {"id": "T", "turns": ["tin tức hôm nay"], "expect": {"language": "vi"}}

    result = run_answer_eval.run_case(provider, case, "system", [], None)

    assert result["passed"] is False
    assert result["grade"]["language_ok"] is False
    assert result["asked_clarify"] is False


def test_runner_marks_a_run_that_ends_waiting_for_the_user_as_unanswered() -> None:
    provider = ScriptedProvider([
        ModelResponse(text=None, tool_calls=[ToolCall("clarify", {"question": "Tin nào?", "response_type": "text"})]),
    ])
    case = {"id": "T", "turns": ["tin tức hôm nay"], "expect": {"language": "vi"}}  # no clarify_reply

    result = run_answer_eval.run_case(provider, case, "system", [], None)

    assert result["answered"] is False and result["passed"] is False
    assert any("no final answer" in f for f in result["grade"]["failures"])


def test_summary_rates_ignore_checks_that_did_not_apply() -> None:
    results = [
        {"passed": True, "asked_clarify": False, "grade": {"language_ok": True, "fresh_ok": None, "failures": []}},
        {"passed": False, "asked_clarify": True, "grade": {"language_ok": False, "fresh_ok": None, "failures": ["x"]}},
    ]

    summary = run_answer_eval.summarize(results)

    assert summary["language_rate"] == 0.5
    assert summary["fresh_rate"] is None
    assert summary["clarify_rate"] == 0.5
    assert summary["answer_pass_rate"] == 0.5

def test_link_found_inside_a_tweet_text_counts_as_grounded() -> None:
    event = {"tool": "timeline", "args": {}, "result": {"items": [
        {"title": "tweet", "summary": "xem tại https://t.co/AbC123 nhé", "url": "https://x.com/sama/status/1"}]}}

    grade = ac.grade_answer("Sam Altman viết: xem tại https://t.co/AbC123", [event], language=None, now=NOW)

    assert grade["grounded_ok"] is True
