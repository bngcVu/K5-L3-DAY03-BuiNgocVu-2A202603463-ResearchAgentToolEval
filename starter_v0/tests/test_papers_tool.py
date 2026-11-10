
from __future__ import annotations

import pytest
import requests

from tools.papers.tool import arxiv_search
import tools.papers.tool as papers_module


# XML giả lập kết quả trả về từ arXiv
ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
      xmlns:arxiv="http://arxiv.org/schemas/atom">

    <opensearch:totalResults>1</opensearch:totalResults>

    <entry>
        <id>https://arxiv.org/abs/2401.12345</id>
        <title>Retrieval Augmented Generation</title>
        <summary>Research about RAG systems.</summary>
        <published>2024-01-10T00:00:00Z</published>
        <updated>2024-01-12T00:00:00Z</updated>

        <author>
            <name>John Smith</name>
        </author>

        <arxiv:primary_category term="cs.IR"/>

        <category term="cs.IR"/>

        <link
            href="https://arxiv.org/pdf/2401.12345"
            title="pdf"
            rel="related"
            type="application/pdf"/>
    </entry>
</feed>
"""


class FakeArxivResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(
                f"HTTP {self.status_code}"
            )


# TEST 1: Happy path
def test_papers_search_returns_parsed_results(monkeypatch):

    captured = {}

    def fake_get(url, *, params=None):
        captured["url"] = url
        captured["params"] = params
        return FakeArxivResponse(ARXIV_XML)

    monkeypatch.setattr(
        papers_module,
        "_arxiv_get",
        fake_get
    )

    result = arxiv_search(
        query="retrieval augmented generation",
        max_results=5,
        sort_by="relevance"
    )

    assert result["tool"] == "arxiv_search"
    assert result["total_results"] == 1
    assert len(result["items"]) == 1

    item = result["items"][0]

    assert item["arxiv_id"] == "2401.12345"
    assert item["title"] == "Retrieval Augmented Generation"
    assert item["authors"] == ["John Smith"]
    assert item["primary_category"] == "cs.IR"
    assert item["pdf_url"] == "https://arxiv.org/pdf/2401.12345"

    assert captured["url"] == papers_module.ARXIV_API_URL
    assert captured["params"]["max_results"] == 5
    assert captured["params"]["sortBy"] == "relevance"


# TEST 2: Bad input
def test_papers_empty_query_returns_error_without_request(monkeypatch):

    called = False

    def fake_get(url, *, params=None):
        nonlocal called
        called = True
        return FakeArxivResponse(ARXIV_XML)

    monkeypatch.setattr(
        papers_module,
        "_arxiv_get",
        fake_get
    )

    result = arxiv_search(query="   ")

    assert result["error"] == "ValueError"
    assert "query" in result["message"]
    assert called is False


# TEST 3: API failure
def test_papers_api_failure_returns_error_dict(monkeypatch):

    def fake_get(url, *, params=None):
        raise requests.Timeout("arXiv API timeout")

    monkeypatch.setattr(
        papers_module,
        "_arxiv_get",
        fake_get
    )

    result = arxiv_search(
        query="machine learning"
    )

    assert result["tool"] == "arxiv_search"
    assert result["error"] == "Timeout"
    assert "timeout" in result["message"].lower()


# TEST 4: Boundary value
def test_papers_zero_max_results_is_clamped_to_one(monkeypatch):

    captured = {}

    def fake_get(url, *, params=None):
        captured["params"] = params
        return FakeArxivResponse(ARXIV_XML)

    monkeypatch.setattr(
        papers_module,
        "_arxiv_get",
        fake_get
    )

    result = arxiv_search(
        query="machine learning",
        max_results=0
    )

    assert "error" not in result
    assert captured["params"]["max_results"] == 1
