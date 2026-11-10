from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT, domain, err, positive_int

# A news request with no subject ("tin tức hôm nay") is valid; Tavily rejects an empty query with 400.
NEWS_FALLBACK_QUERY = "tin tức nổi bật"


def web_search(query: str = "", topic: str = "general", timeframe: str | None = "week", max_results: int = 5) -> dict[str, Any]:
    try:
        query = str(query or "").strip()
        if not query:
            if topic == "news":
                query = NEWS_FALLBACK_QUERY
            else:
                raise ValueError("query must not be empty")
        max_results = positive_int(max_results, 5, "max_results")
        key = os.getenv("TAVILY_API_KEY")
        if not key:
            raise RuntimeError("Missing TAVILY_API_KEY env var")
        body: dict[str, Any] = {"query": query, "topic": topic, "max_results": max_results, "search_depth": "basic"}
        if timeframe:
            body["time_range"] = timeframe
        response = requests.post(
            "https://api.tavily.com/search",
            json=body,
            headers={"Authorization": f"Bearer {key}"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        items = []
        for item in data.get("results", []):
            row = {
                "title": item.get("title"),
                "url": item.get("url"),
                "source": domain(item.get("url", "")),
                "summary": item.get("content"),
                "score": item.get("score"),
            }
            # Tavily returns the publish date for topic=news. Expose it so the agent can check "today".
            if item.get("published_date"):
                row["published_date"] = item["published_date"]
            items.append(row)
        return {"tool": "web_search", "query": query, "topic": topic, "timeframe": timeframe, "items": items}
    except Exception as exc:
        return err("web_search", exc)

