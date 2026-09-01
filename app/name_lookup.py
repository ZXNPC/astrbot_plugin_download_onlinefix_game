"""Steam 商店名称解析：用中文关键词查官方英文名。

路线：storesearch（l=schinese）→ 取第一个 type=app 且中文名与查询词有 CJK 重叠的命中；
若该命中名称已不含中文则直接使用，否则用 appdetails（l=english）取官方英文名。
任何一步失败均返回 None，由调用方回退原词。
"""

from __future__ import annotations

import re

from .http_client import build_client
from .matcher import normalize

STORESEARCH_URL = "https://store.steampowered.com/api/storesearch/"
APPDETAILS_URL = "https://store.steampowered.com/api/appdetails/"

_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")
_MIN_OVERLAP_RUN = 2


def contains_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text or ""))


def has_cjk_overlap(query: str, name: str) -> bool:
    """查询词与返回名称是否有共同中文片段（防止搜到无关游戏）。

    使用归一化后的连续中文串做包含判断（如「黑神话悟空」⊂「黑神话悟空豪华版」），
    且只考虑长度 >= 2 的片段，避免单个常用汉字造成误匹配。
    """
    q_runs = [r for r in _CJK_RE.findall(normalize(query or "")) if len(r) >= _MIN_OVERLAP_RUN]
    n_runs = [r for r in _CJK_RE.findall(normalize(name or "")) if len(r) >= _MIN_OVERLAP_RUN]
    if not q_runs or not n_runs:
        return False
    for q in q_runs:
        for n in n_runs:
            if q in n or n in q:
                return True
    return False


def extract_search_hit(payload, query: str):
    """从 storesearch 响应提取候选命中；无合格命中返回 None。

    返回 {"id": int, "name": str}；name 可能是中文名（需再取英文名）或已是英文名。
    """
    try:
        items = payload.get("items") or []
    except AttributeError:
        return None
    for item in items:
        if not isinstance(item, dict):
            continue
        if (item.get("type") or "") != "app":
            continue
        name = (item.get("name") or "").strip()
        if not name:
            continue
        if contains_cjk(name) and not has_cjk_overlap(query, name):
            continue
        try:
            appid = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        return {"id": appid, "name": name}
    return None


def extract_appdetails_name(payload, appid: int):
    """从 appdetails 响应提取英文名；失败返回 None。"""
    try:
        data = payload.get(str(appid))
    except AttributeError:
        return None
    if not isinstance(data, dict) or not data.get("success"):
        return None
    inner = data.get("data")
    if not isinstance(inner, dict):
        return None
    name = (inner.get("name") or "").strip()
    return name or None


async def resolve_english_name(term: str, *, timeout: float = 10.0):
    """解析中文游戏名的官方英文名；失败返回 None。"""
    term = (term or "").strip()
    if not term:
        return None
    async with build_client(timeout) as client:
        resp = await client.get(
            STORESEARCH_URL,
            params={"term": term, "l": "schinese", "cc": "cn"},
        )
        resp.raise_for_status()
        hit = extract_search_hit(resp.json(), term)
        if hit is None:
            return None
        if not contains_cjk(hit["name"]):
            return hit["name"]
        resp2 = await client.get(
            APPDETAILS_URL,
            params={"appids": hit["id"], "l": "english", "cc": "us"},
        )
        resp2.raise_for_status()
        return extract_appdetails_name(resp2.json(), hit["id"])