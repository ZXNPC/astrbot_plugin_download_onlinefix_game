"""online-fix.me 搜索与详情页解析。"""

from __future__ import annotations

import asyncio
import random
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .http_client import fetch
from .result import Candidate, DownloadLink

SEARCH_URL = "https://online-fix.me/index.php"
GAME_PATH_RE = re.compile(r"/games/", re.IGNORECASE)
ARCHIVE_RE = re.compile(r"\.(rar|zip|7z)(?:\?|$)", re.IGNORECASE)
NETDISK_RE = re.compile(
    r"mega\.nz|pixeldrain|drive\.google|mediafire|gofile\.io|modsfire|buzzheavier|1fichier|workupload|krakenfiles|wdupload|dropbox",
    re.IGNORECASE,
)
PASSWORD = "online-fix.me"


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
    """解析详情页下载链接，按优先级：服务器直链＞Drive＞Hosters＞网盘。"""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    seen = set()
    for a in soup.select("a[href]"):
        href = (a.get("href") or "").strip()
        lower = href.lower()
        if "uploads.online-fix.me" in lower:
            label = "服务器直链目录"
        elif "drive.online-fix.me" in lower:
            label = "Online-Fix Drive"
        elif "hosters.online-fix.me" in lower or ":2053" in lower:
            label = "Online-Fix Hosters"
        elif NETDISK_RE.search(lower):
            label = "网盘"
        else:
            continue
        if href not in seen:
            seen.add(href)
            links.append(DownloadLink(label, href))
    return Candidate(
        source="online-fix.me",
        title=hit.get("title", ""),
        page_url=hit.get("page_url", ""),
        kind="full",
        links=links,
        password=PASSWORD,
    )


async def resolve_rar_link(client, dir_url: str, max_depth: int = 2):
    """在 uploads.online-fix.me 目录列表里定位 Fix Repair 的 .rar。"""
    current = dir_url
    for _ in range(max_depth):
        resp = await fetch(client, current)
        soup = BeautifulSoup(resp.text, "html.parser")
        hrefs = []
        for a in soup.select("a[href]"):
            href = (a.get("href") or "").strip()
            if href:
                hrefs.append(urljoin(current, href))
        archives = [u for u in hrefs if ARCHIVE_RE.search(u)]
        if archives:
            for u in archives:
                if "fix" in u.lower() or "repair" in u.lower():
                    return u
            return archives[0]
        repair_dir = next(
            (
                u
                for u in hrefs
                if u.endswith("/") and ("fix" in u.lower() or "repair" in u.lower())
            ),
            None,
        )
        if repair_dir:
            current = repair_dir
            continue
        return None
    return None


async def search_onlinefix(client, query: str):
    resp = await fetch(
        client,
        SEARCH_URL,
        params={"do": "search", "subaction": "search", "story": query},
    )
    return parse_search_html(resp.text)


async def resolve_detail(client, hit: dict) -> Candidate:
    """抓取详情页并尽量解析出直链。"""
    await asyncio.sleep(random.uniform(1.0, 2.0))  # 反爬：请求间隔
    resp = await fetch(client, hit["page_url"])
    candidate = parse_detail_html(resp.text, hit)
    uploads_dir = next(
        (link.url for link in candidate.links if "uploads.online-fix.me" in link.url),
        None,
    )
    if uploads_dir:
        try:
            rar = await resolve_rar_link(client, uploads_dir)
        except Exception:
            rar = None  # 目录解析失败时保留原始服务器目录链接
        if rar:
            candidate.links.insert(0, DownloadLink("直链 (.rar)", rar))
    if not candidate.links:
        candidate.links.append(DownloadLink("详情页", hit.get("page_url", "")))
    return candidate


def fallback_candidate(hit: dict) -> Candidate:
    return Candidate(
        source="online-fix.me",
        title=hit.get("title", ""),
        page_url=hit.get("page_url", ""),
        kind="full",
        links=[DownloadLink("详情页", hit.get("page_url", ""))],
        password=PASSWORD,
    )
