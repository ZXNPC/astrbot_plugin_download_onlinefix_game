import asyncio

import httpx
import pytest

from app.http_client import fetch, is_challenge_page


def test_challenge_detection():
    assert is_challenge_page("<title>Just a moment...</title>")
    assert not is_challenge_page("<title>CyberCorp по сети бесплатно</title>")


def test_fetch_retries_challenge_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(200, text="<title>Just a moment...</title>")
        return httpx.Response(200, text="<html>ok</html>")

    async def run():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            resp = await fetch(client, "https://example.com", retries=2, retry_delay=0)
        return resp.text

    assert asyncio.run(run()) == "<html>ok</html>"
    assert calls["n"] == 3


def test_fetch_raises_when_always_blocked():
    def handler(request):
        return httpx.Response(200, text="<title>captcha</title>")

    async def run():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            await fetch(client, "https://example.com", retries=1, retry_delay=0)

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(run())
