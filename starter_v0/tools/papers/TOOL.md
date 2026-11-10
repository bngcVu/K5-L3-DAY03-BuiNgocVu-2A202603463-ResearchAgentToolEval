---
name: papers
track: bonus
kind: live_api
provider: arXiv API
requires_env: []
inputs: [query, max_results, sort_by]
outputs: [items, total_results]
side_effect: false
---

# papers

Searches scientific papers using the official arXiv Atom API.

## Usage

- Use when users request scientific papers or research publications.
- Supports keyword-based searching.
- Supports relevance, latest updated, and submission date sorting.
- Returns paper title, authors, abstract, arXiv ID, publication date and PDF URL.
- Maximum 10 results per request.
- Does not require an API key.
- Waits at least 3 seconds between requests within the same process.

## Input

- query: Required, non-empty research topic.
- max_results: Number of results, from 1 to 10. Default 5.
- sort_by: relevance, lastUpdatedDate or submittedDate.

## Output

- items: List of scientific papers.
- total_results: Total matching results reported by arXiv.