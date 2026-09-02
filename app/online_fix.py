"""online-fix.me 搜索与详情页解析。"""

from __future__ import annotations

import asyncio
import random
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .http_client import fetch
from .result import Candidate, DownloadLink

SEARCH_URL = "https://online-fix.me/index.php"
GAME_PATH_RE = re.compile(r"/games/", re.IGNORECASE)
NETDISK_RE = re.compile(
    r"mega\.nz|pixeldrain|drive\.google|mediafire|gofile\.io|modsfire|buzzheavier|1fichier|workupload|krakenfiles|wdupload|dropbox",
    re.IGNORECASE,
)
PASSWORD = "online-fix.me"


def is_onlinefix_guarded_url(url: str) -> bool:
    """判断是否为 online-fix.me 的站内下载地址（依赖 Referer，不能独立外发）。"""
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    host = (parsed.hostname or "").lower()
    if host == "online-fix.me":
        try:
            return parsed.port == 2053
        except ValueError:
            return False
    return host.endswith(".online-fix.me")


def parse_search_html(html: str):
    """解析搜索结果页；只保留 /games/ 分类命中（忽略 updates/DLC）。"""
    soup = BeautifulSoup(html, "html.parser")
    hits = []
    seen = set()
    for item in soup.select("div.news.news-search div.article.clr"):
        title_el = item.select_one("h2.title")
        link_el = item.select_one("a.big-link")
        if link_el is None and title_el is not None:
            link_el = title_el.find("a")
        if title_el is None or link_el is None:
            continue
        url = (link_el.get("href") or "").strip()
        if not GAME_PATH_RE.search(url):
            continue
        title = title_el.get_text(" ", strip=True)
        if not title or url in seen:
            continue
        seen.add(url)
        hits.append({"title": title, "page_url": urljoin("https://online-fix.me", url)})
    return hits


def parse_detail_html(html: str, hit: dict) -> Candidate:
    """只保留可独立访问的外部网盘链接。

    站内服务器/Drive/Hosters 链接依赖 Referer，详情页外直接打开会 401，
    因此不单独外发，统一以详情页作为下载入口。
    """
    soup = BeautifulSoup(html, "html.parser")
    links = []
    seen = set()
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        if is_onlinefix_guarded_url(href) or not NETDISK_RE.search(href):
            continue
        if href not in seen:
            seen.add(href)
            links.append(DownloadLink("网盘", href))
    return Candidate(
        source="online-fix.me",
        title=hit.get("title", ""),
        page_url=hit.get("page_url", ""),
        kind="full",
        links=links,
        password=PASSWORD,
    )


async def search_onlinefix(client, query: str):
    resp = await fetch(
        client,
        SEARCH_URL,
        params={"do": "search", "subaction": "search", "story": query},
    )
    return parse_search_html(resp.text)


async def resolve_detail(client, hit: dict) -> Candidate:
    """抓取详情页并返回可独立访问的链接；无外链时由 page_url 提供入口。"""
    await asyncio.sleep(random.uniform(1.0, 2.0))  # 反爬：请求间隔
    resp = await fetch(client, hit["page_url"])
    return parse_detail_html(resp.text, hit)


def fallback_candidate(hit: dict) -> Candidate:
    return Candidate(
        source="online-fix.me",
        title=hit.get("title", ""),
        page_url=hit.get("page_url", ""),
        kind="full",
        links=[],
        password=PASSWORD,
    )
