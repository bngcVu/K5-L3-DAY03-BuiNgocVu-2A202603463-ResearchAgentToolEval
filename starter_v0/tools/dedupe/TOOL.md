---
name: dedupe
track: core
kind: local_formatter
requires_env: []
inputs: [items, by, limit]
outputs: [items, item_count, removed_count, skipped_invalid, duplicates]
side_effect: false
---
# dedupe

Removes duplicate items from results that were already collected (for example when
`lookup` and `social_search` return the same story). It does not fetch any data.

- Keeps the **first** occurrence and preserves order.
- `by="url"` (default) compares normalized URLs: ignores `www.`, `utm_*` / tracking
  params, a trailing `/` and `#fragment`, so `https://www.x.com/a/?utm_source=t` equals
  `https://x.com/a`.
- `by="title"` compares titles ignoring case, accents and punctuation.
- If the chosen field is missing on an item, it falls back to the other field; an item
  with neither is kept (never dropped by guess).
- `limit` truncates the result after dedupe (`0` = no limit).
- Bad input (non-list `items`, `by` outside the enum, negative or non-numeric `limit`)
  returns an error dict instead of raising.

Typical flow: `lookup` + `social_search` -> `dedupe` -> `format`.
