"""中文→英文翻译（Google 免费端点），支持专用代理。"""

from __future__ import annotations

import re

import httpx

TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
_CJK_RE = re.compile(r"[\u4e00-\u9fff]")


def contains_cjk(text: str) -> bool:
    return bool(_CJK_RE.search(text or ""))


def extract_translation(payload) -> str:
    parts = []
    try:
        segments = payload[0]
    except (TypeError, IndexError, KeyError):
        return ""
    for seg in segments or []:
        if isinstance(seg, list) and seg and isinstance(seg[0], str):
            parts.append(seg[0])
    return "".join(parts).strip()


async def translate_to_english(
    text: str,
    *,
    enabled: bool = True,
    proxy: str = "",
    timeout: float = 10.0,
) -> str:
    text = (text or "").strip()
    if not text or not enabled or not contains_cjk(text):
        return text
    params = {"client": "gtx", "sl": "zh-CN", "tl": "en", "dt": "t", "q": text}
    kwargs = {
        "timeout": httpx.Timeout(timeout),
        "headers": {"User-Agent": "Mozilla/5.0"},
    }
    if proxy:
        kwargs["proxy"] = proxy
    async with httpx.AsyncClient(**kwargs) as client:
        resp = await client.get(TRANSLATE_URL, params=params)
        resp.raise_for_status()
        payload = resp.json()
    return extract_translation(payload) or text
