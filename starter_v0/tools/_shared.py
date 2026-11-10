from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
TIMEOUT = 30


def err(tool: str, exc: Exception) -> dict[str, Any]:
    return {"tool": tool, "error": type(exc).__name__, "message": str(exc)}


def domain(url: str) -> str:
    try:
        return urlparse(url).netloc.replace("www.", "")
    except Exception:
        return ""


def fold_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def terms(text: str) -> set[str]:
    stopwords = {
        "a", "an", "and", "are", "as", "at", "by", "for", "from", "in", "is", "of", "on", "or", "the", "to",
        "ban", "bao", "can", "cho", "co", "cua", "duoc", "gi", "giup", "la", "lam", "minh", "mot", "nay",
        "nen", "the", "thi", "trong", "va", "ve", "voi",
    }
    folded = fold_text(text)
    return {term for term in re.findall(r"[a-z0-9]+", folded) if len(term) > 1 and term not in stopwords}



def positive_int(value: Any, default: int, name: str = "value") -> int:
    """Coerce a model-supplied count to an int >= 1.

    None / "" mean "not provided" -> `default`. Numeric strings ("5") are accepted.
    0, negatives and non-numeric values raise ValueError so the tool returns an error
    dict instead of silently substituting the default (the old `int(x or default)` bug).
    """
    if value is None or value == "":
        return default
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be an integer >= 1, got {value!r}") from None
    if number < 1:
        raise ValueError(f"{name} must be an integer >= 1, got {value!r}")
    return number
