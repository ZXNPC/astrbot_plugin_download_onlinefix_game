"""httpx 客户端封装：随机 UA、统一超时、反爬挑战检测与重试。"""

from __future__ import annotations

import asyncio
import random

import httpx

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
]

CHALLENGE_MARKERS = (
    "just a moment",
    "attention required",
    "captcha",
    "verify you are human",
    "cf-chl",
)


def is_challenge_page(text) -> bool:
    lower = (text or "")[:4000].lower()
    return any(marker in lower for marker in CHALLENGE_MARKERS)


def build_client(timeout=60.0, proxy=""):
    kwargs = {
        "timeout": httpx.Timeout(timeout),
        "follow_redirects": True,
        "headers": {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ru;q=0.7",
        },
    }
    if proxy:
        kwargs["proxy"] = proxy
    return httpx.AsyncClient(**kwargs)


async def fetch(client, url, *, params=None, retries=1, retry_delay=2.0):
    """GET 请求；遇到反爬拦截或限流时按指数间隔重试一次。"""
    for attempt in range(retries + 1):
        try:
            resp = await client.get(url, params=params)
        except httpx.HTTPError as exc:
            if attempt < retries:
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
            raise
        blocked = resp.status_code in (403, 429, 503) or is_challenge_page(resp.text)
        if blocked:
            if attempt < retries:
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
            raise httpx.HTTPStatusError(
                f"blocked by anti-bot (status {resp.status_code})",
                request=resp.request,
                response=resp,
            )
        resp.raise_for_status()
        return resp
    raise RuntimeError("unreachable")
