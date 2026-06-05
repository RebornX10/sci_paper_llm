from __future__ import annotations

import re

import pandas as pd
from rank_bm25 import BM25Okapi

from app.config import CONFIG

_R = CONFIG["retrieval"]
_TOKEN = re.compile(r"[a-z0-9]+")


def _text(v) -> str:
    return v if isinstance(v, str) else ""


def _authors(v) -> list:
    if isinstance(v, (list, tuple)):
        return list(v)
    if hasattr(v, "tolist"):
        return list(v.tolist())
    return []


def _tok(s: str) -> list:
    return _TOKEN.findall(s.lower())


# BM25 index is expensive to build, so cache it per corpus. The DataFrame is
# replaced wholesale on every new build, so its identity is a safe cache key;
# we pin the df in the cache to keep that id valid.
_cache: dict = {"id": None, "df": None, "bm25": None, "rows": None}


def _index(df: pd.DataFrame):
    if _cache["id"] == id(df) and _cache["bm25"] is not None:
        return _cache["bm25"], _cache["rows"]
    rows = df.to_dict("records")
    tokens = []
    for r in rows:
        blob = f"{_text(r.get('title'))} {_text(r.get('abstract'))} {_text(r.get('content'))}"
        tokens.append(_tok(blob) or ["_"])
    bm25 = BM25Okapi(tokens)
    _cache.update(id=id(df), df=df, bm25=bm25, rows=rows)
    return bm25, rows


def _best_excerpt(text: str, q_tokens: set, size: int) -> str:
    """Return the most query-relevant ~`size`-char window of `text` (with
    ellipses), instead of always taking the document's head."""
    if len(text) <= size:
        return text
    step = max(1, size // 2)
    best, best_start, best_score = text[:size], 0, -1
    for start in range(0, len(text) - size + 1, step):
        window = text[start:start + size].lower()
        score = sum(window.count(t) for t in q_tokens)
        if score > best_score:
            best_score, best_start, best = score, start, text[start:start + size]
    prefix = "…" if best_start > 0 else ""
    suffix = "…" if best_start + size < len(text) else ""
    return f"{prefix}{best.strip()}{suffix}"


def build_context(df: pd.DataFrame, question: str, k: int = None, budget: int = None):
    k = k or _R["top_k"]
    budget = budget or _R["context_budget"]
    bm25, rows = _index(df)
    q_tokens = _tok(question) or ["_"]
    scores = bm25.get_scores(q_tokens)
    order = sorted(range(len(rows)), key=lambda i: scores[i], reverse=True)[:k]

    q_set = set(q_tokens)
    per_excerpt = max(200, budget // max(1, k))
    parts, sources, used = [], [], 0
    for i in order:
        row = rows[i]
        body = _text(row.get("content")) or _text(row.get("abstract"))
        authors = _authors(row.get("authors"))
        idx = len(parts) + 1
        excerpt = _best_excerpt(body, q_set, per_excerpt)
        block = (
            f"[{idx}] Title: {_text(row.get('title'))}\n"
            f"Authors: {', '.join(authors[:6])}\n"
            f"Journal: {_text(row.get('journal'))} ({_text(row.get('date'))})\n"
            f"Excerpt: {excerpt}\n---"
        )
        if used + len(block) > budget and parts:
            break
        parts.append(block)
        used += len(block)
        sources.append({"title": _text(row.get("title")) or None,
                        "authors": authors[:6],
                        "journal": _text(row.get("journal")) or None,
                        "date": _text(row.get("date")) or None,
                        "snippet": (body[:240].strip() or None)})
    return "\n".join(parts), sources
