"""gamer520.com 搜索与文章页解析（游戏本体网盘链接）。"""

from __future__ import annotations

import asyncio
import random
import re
from html import unescape
from urllib.parse import parse_qs, unquote, urlparse

from bs4 import BeautifulSoup

from .http_client import fetch
from .result import Candidate, DownloadLink

SEARCH_URL = "https://www.gamer520.com/"
ARTICLE_URL_RE = re.compile(r"^https?://www\.gamer520\.com/\d+\.html$", re.IGNORECASE)
NETDISK_RE = re.compile(
    r"pan\.baidu\.com|pan\.xunlei\.com|pan\.quark\.cn|quark\.cn|aliyundrive|alipan\.com|123pan|ctfile|lanzou|lanzn|weiyun\.com|115\.com|mega\.nz|mediafire|pixeldrain|gofile\.io|modsfire|buzzheavier|1fichier|workupload|krakenfiles|wdupload|send\.cm|tianyancha",
    re.IGNORECASE,
)
PWD_RE = re.compile(r"pwd=([a-zA-Z0-9]+)", re.IGNORECASE)
PASSWORD_RE = re.compile(r"解压密码\s*[:：]\s*([^\s|<]+)")


def parse_search_html(html: str):
    soup = BeautifulSoup(html, "html.parser")
    hits = []
    seen = set()
    for article in soup.select("article.post, article"):
        a = article.select_one("h2.entry-title a[href]")
        if a is None:
            a = article.select_one("a[href]")
        if a is None:
            continue
        href = (a.get("href") or "").strip()
        if not ARTICLE_URL_RE.fullmatch(href):
            continue
        title = (a.get_text(" ", strip=True) or a.get("title") or "").strip()
        if not title or href in seen:
            continue
        seen.add(href)
        hits.append({"title": title, "page_url": href})
    return hits


def parse_article_html(html: str, hit: dict) -> Candidate:
    """解析文章页网盘链接（普通链接 + 二维码 data 参数）。"""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    seen = set()
    for a in soup.select("a[href]"):
        href = unescape((a.get("href") or "").strip())
        if not NETDISK_RE.search(href) or href in seen:
            continue
        seen.add(href)
        label = (a.get_text(" ", strip=True) or "网盘")[:24] or "网盘"
        links.append(DownloadLink(label, href))
    # 百度/夸克等网盘常以二维码图片呈现，data 参数里带真实链接
    for img in soup.select("img[src]"):
        src = img.get("src", "")
        if "qrserver" not in src and "qrcode" not in src:
            continue
        for data in parse_qs(urlparse(src).query).get("data", []):
            url = unquote(data)
            if NETDISK_RE.search(url) and url not in seen:
                seen.add(url)
                links.append(DownloadLink("网盘（扫码）", url))
    for link in links:
        m = PWD_RE.search(link.url)
        if m:
            link.extra = f"提取码: {m.group(1)}"
    m = PASSWORD_RE.search(html)
    password = m.group(1).strip() if m else ""
    if not links:
        links.append(DownloadLink("文章页", hit.get("page_url", "")))
    return Candidate(
        source="gamer520.com",
        title=hit.get("title", ""),
        page_url=hit.get("page_url", ""),
        kind="body",
        links=links,
        password=password,
    )


async def search_gamer520(client, query: str):
    resp = await fetch(client, SEARCH_URL, params={"s": query})
    return parse_search_html(resp.text)


async def resolve_article(client, hit: dict) -> Candidate:
    await asyncio.sleep(random.uniform(0.8, 1.5))  # 反爬：请求间隔
    resp = await fetch(client, hit["page_url"])
    return parse_article_html(resp.text, hit)


def fallback_candidate(hit: dict) -> Candidate:
    return Candidate(
        source="gamer520.com",
        title=hit.get("title", ""),
        page_url=hit.get("page_url", ""),
        kind="body",
        links=[DownloadLink("文章页", hit.get("page_url", ""))],
    )
