"""游戏名规范化与模糊匹配。"""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

MATCH_THRESHOLD = 0.3

_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
_LATIN_RE = re.compile(r"[a-z0-9]+")


def normalize(text: str) -> str:
    """去全角、去标点空格、转小写，用于匹配和缓存键。"""
    s = unicodedata.normalize("NFKC", text or "")
    s = s.lower()
    return re.sub(r"[\W_]+", "", s, flags=re.UNICODE)


def _tokenize(text: str) -> set:
    tokens = set(_LATIN_RE.findall(text))
    tokens.update(_CJK_RE.findall(text))
    return tokens


def score(query: str, title: str) -> float:
    q, t = normalize(query), normalize(title)
    if not q or not t:
        return 0.0
    if q == t:
        return 1.0
    scores = [SequenceMatcher(None, q, t).ratio()]
    if q in t or t in q:
        ratio = min(len(q), len(t)) / max(len(q), len(t))
        scores.append(0.85 + 0.15 * ratio)
    q_tokens, t_tokens = _tokenize(q), _tokenize(t)
    if q_tokens and t_tokens:
        inter = len(q_tokens & t_tokens)
        union = len(q_tokens | t_tokens)
        if union:
            scores.append(inter / union)
        scores.append(inter / len(q_tokens))
    return max(scores)


def rank_hits(hits, query: str, limit: int):
    """按匹配度过滤并排序，返回前 limit 个命中。"""
    scored = []
    for hit in hits:
        s = score(query, hit.get("title", ""))
        if s >= MATCH_THRESHOLD:
            scored.append((s, hit))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [hit for _, hit in scored[:limit]]
