"""Regression tests for the bugs found after v3 and fixed inside v3 (Challenge+ of Step 4b).

Each test pins one behaviour that was wrong before:
- lookup forwarded an empty query to Tavily (HTTP 400) for "tin tức hôm nay".
- limit=0 / top_k=0 / max_results=0 were silently replaced by the default (`int(x or default)`).
- format left a dangling " - " for items without url/source.
- run_eval graded a call as PASS even when a required arg was empty or the tool errored.
"""
from __future__ import annotations

import pytest

import run_eval
from conftest import FakeResponse
from tools import TOOL_FUNCTIONS

lookup_tool = TOOL_FUNCTIONS["lookup"]
timeline_tool = TOOL_FUNCTIONS["timeline"]
social_search_tool = TOOL_FUNCTIONS["social_search"]
policy_tool = TOOL_FUNCTIONS["policy"]
format_tool = TOOL_FUNCTIONS["format"]


# ---------------- lookup: empty query ----------------

@pytest.mark.parametrize("empty", ["", "   ", None])
def test_lookup_news_with_empty_query_falls_back_to_trending_news(monkeypatch, fake_http, empty) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    calls = fake_http(FakeResponse({"results": []}))

    result = lookup_tool(query=empty, topic="news", timeframe="day")

    assert len(calls) == 1
    assert calls[0]["json"]["query"] == "tin tức nổi bật"
    assert calls[0]["json"]["topic"] == "news"
    assert result["query"] == "tin tức nổi bật"
    assert "error" not in result


def test_lookup_general_with_empty_query_returns_error_and_sends_no_request(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    calls = fake_http(FakeResponse({"results": []}))

    result = lookup_tool(query="  ", topic="general")

    assert result["error"] == "ValueError"
    assert "query" in result["message"]
    assert calls == []


def test_lookup_keeps_a_real_query_untouched_and_trims_it(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    calls = fake_http(FakeResponse({"results": []}))

    lookup_tool(query="  robotics ", topic="news")

    assert calls[0]["json"]["query"] == "robotics"


# ---------------- count args: 0 must not silently become the default ----------------

def test_lookup_max_results_zero_returns_error_and_sends_no_request(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    calls = fake_http(FakeResponse({"results": []}))

    result = lookup_tool(query="AI", max_results=0)

    assert result["error"] == "ValueError"
    assert "max_results" in result["message"]
    assert calls == []


def test_lookup_accepts_numeric_string_max_results(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test-key")
    calls = fake_http(FakeResponse({"results": []}))

    lookup_tool(query="AI", max_results="3")

    assert calls[0]["json"]["max_results"] == 3


@pytest.mark.parametrize("tool, kwargs", [
    (timeline_tool, {"screenname": "sama"}),
    (social_search_tool, {"query": "OpenAI"}),
])
def test_twitter_tools_limit_zero_returns_error_and_sends_no_request(monkeypatch, fake_http, tool, kwargs) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "rk-test")
    calls = fake_http(FakeResponse({"timeline": []}))

    result = tool(limit=0, **kwargs)

    assert result["error"] == "ValueError"
    assert "limit" in result["message"]
    assert calls == []


def test_timeline_accepts_numeric_string_limit(monkeypatch, fake_http) -> None:
    monkeypatch.setenv("RAPIDAPI_KEY", "rk-test")
    raw = [{"screen_name": "sama", "tweet_id": str(n), "text": f"t{n}"} for n in range(1, 6)]
    fake_http(FakeResponse({"timeline": raw}))

    assert len(timeline_tool(screenname="sama", limit="2")["items"]) == 2


def test_policy_top_k_zero_returns_error_instead_of_default_three() -> None:
    result = policy_tool(query="confidential customer data", top_k=0)

    assert result["error"] == "ValueError"
    assert "top_k" in result["message"]


def test_policy_top_k_one_returns_at_most_one_result() -> None:
    result = policy_tool(query="confidential customer data", top_k=1)

    assert 1 <= len(result["results"]) <= 1


# ---------------- format: dangling separator ----------------

def test_format_bullet_without_url_or_source_has_no_dangling_dash() -> None:
    markdown = format_tool(items=[{"title": "Tin A"}], template="bullets")["markdown"]

    assert markdown == "- Tin A"


def test_format_bullet_with_url_still_shows_source_link() -> None:
    markdown = format_tool(items=[{"title": "Tin A", "url": "https://example.com/a"}], template="bullets")["markdown"]

    assert markdown == "- Tin A - [example.com](https://example.com/a)"


# ---------------- run_eval grading ----------------

def _case(expected_args: dict) -> dict:
    return {
        "id": "X", "phase": "B", "failure_type": "wrong_arg_value",
        "expect": {"tool_calls": [{"name": "lookup", "args": expected_args}]},
    }


def test_eval_fails_a_call_whose_required_query_is_empty_even_if_other_args_match() -> None:
    result = run_eval.evaluate_phase_b(
        _case({"topic": "news", "timeframe": "day"}),
        [{"name": "lookup", "args": {"query": "", "topic": "news", "timeframe": "day"}}],
        None,
    )

    assert result["passed"] is False
    assert result["observed_mismatch"] == "empty_required_arg"
    assert any("lookup.query" in failure for failure in result["failures"])


def test_eval_passes_the_same_call_when_query_is_not_empty() -> None:
    result = run_eval.evaluate_phase_b(
        _case({"topic": "news", "timeframe": "day"}),
        [{"name": "lookup", "args": {"query": "tin tức", "topic": "news", "timeframe": "day"}}],
        None,
    )

    assert result["passed"] is True
    assert result["failures"] == []


def test_summary_reports_tool_success_rate() -> None:
    def item(tool_results):
        return {"phase": "B", "result": {"passed": True, "routing_correct": True, "args_correct": True},
                "tool_results": tool_results}

    summary = run_eval.summarize([
        item([{"name": "lookup", "result": {"error": "HTTPError", "message": "400"}}]),
        item([{"name": "lookup", "result": {"items": []}}, {"name": "clarify", "result": {"awaiting_user": True}}]),
    ])

    assert summary["tool_success_rate"] == pytest.approx(0.6667, abs=1e-4)


def test_summary_omits_tool_success_rate_when_no_tool_ran() -> None:
    summary = run_eval.summarize([
        {"phase": "B", "result": {"passed": True, "routing_correct": True, "args_correct": True}, "tool_results": []},
    ])

    assert "tool_success_rate" not in summary
