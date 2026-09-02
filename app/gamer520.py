"""gamer520.com 搜索与文章页解析（游戏本体网盘链接）。"""

from __future__ import annotations

import asyncio
import json
import random
import re
from html import unescape
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from .http_client import fetch
from .result import Candidate, DownloadLink

SEARCH_URL = "https://www.gamer520.com/"
ARTICLE_URL_RE = re.compile(
    r"^https?://(?:www\.)?(?:gamer520|gamers520)\.com/\d+\.html$",
    re.IGNORECASE,
)
NETDISK_RE = re.compile(
    r"pan\.baidu\.com|pan\.xunlei\.com|pan\.quark\.cn|quark\.cn|aliyundrive|alipan\.com|123pan|ctfile|lanzou|lanzn|weiyun\.com|115\.com|mega\.nz|mediafire|pixeldrain|gofile\.io|modsfire|buzzheavier|1fichier|workupload|krakenfiles|wdupload|send\.cm|tianyancha",
    re.IGNORECASE,
)
# 这些分类不是游戏本体：修改器、金手指、模拟器/主题等。
NON_GAME_CATEGORY_SLUGS = (
    "xgq",
    "jinshouzhi",
    "zhangji",
    "console-emulator",
    "zhuti",
)
PWD_RE = re.compile(r"pwd=([a-zA-Z0-9]+)", re.IGNORECASE)
PASSWORD_RE = re.compile(r"解压密码\s*[:：]\s*([^\s|<]+)")
REDIRECT_RE = re.compile(r"""window\.location\s*=\s*['"]([^'"]+)['"]""", re.IGNORECASE)
MAX_GATE_DEPTH = 3

HOST_LABELS = (
    ("pan.baidu.com", "百度网盘"),
    ("pan.quark.cn", "夸克网盘"),
    ("quark.cn", "夸克网盘"),
    ("pan.xunlei.com", "迅雷云盘"),
    ("xunlei.com", "迅雷云盘"),
    ("aliyundrive.com", "阿里云盘"),
    ("alipan.com", "阿里云盘"),
    ("123pan", "123网盘"),
    ("ctfile", "城通网盘"),
    ("weiyun.com", "微云"),
    ("115.com", "115网盘"),
    ("mega.nz", "Mega"),
    ("mediafire", "MediaFire"),
    ("pixeldrain", "PixelDrain"),
    ("gofile.io", "GoFile"),
    ("modsfire", "ModsFire"),
    ("buzzheavier", "Buzzheavier"),
    ("1fichier", "1fichier"),
    ("workupload", "WorkUpload"),
    ("krakenfiles", "KrakenFiles"),
    ("wdupload", "WDUpload"),
    ("lanzou", "蓝奏云"),
    ("lanzn", "蓝奏云"),
    ("send.cm", "Send"),
    ("tianyancha", "天翼云盘"),
)


def _content_container(soup: BeautifulSoup) -> BeautifulSoup:
    """只扫描正文区，避免把导航/侧栏里的网盘链接误当下载链接。"""
    return soup.select_one(".entry-content") or soup.select_one("article") or soup


def _netdisk_label(url: str, fallback: str = "网盘") -> str:
    lower = url.lower()
    for host, label in HOST_LABELS:
        if host in lower:
            return label
    return (fallback or "网盘")[:24] or "网盘"


def _extract_code(link: DownloadLink) -> None:
    m = PWD_RE.search(link.url)
    if m and not link.extra:
        link.extra = f"提取码: {m.group(1)}"


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
        category_hrefs = [
            (cat.get("href") or "").lower()
            for cat in article.select(".meta-category a[href]")
        ]
        if any(slug in href for href in category_hrefs for slug in NON_GAME_CATEGORY_SLUGS):
            continue
        title = (a.get_text(" ", strip=True) or a.get("title") or "").strip()
        if not title or href in seen:
            continue
        seen.add(href)
        hits.append({"title": title, "page_url": href})
    return hits


def _extract_download_links(soup: BeautifulSoup, page_url: str):
    """提取正文中的网盘链接（普通 <a> + 二维码 data 参数）。"""
    content = _content_container(soup)
    links = []
    seen = set()
    for a in content.select("a[href]"):
        href = unescape((a.get("href") or "").strip())
        if not NETDISK_RE.search(href) or href in seen:
            continue
        seen.add(href)
        label = a.get_text(" ", strip=True)
        if not label or label.lower() in {"下载", "点击下载", "获取资源", "获取链接"}:
            label = _netdisk_label(href)
        links.append(DownloadLink(label, href))
    # 百度/夸克等网盘常以二维码图片呈现，data 参数里带真实链接
    for img in content.select("img[src]"):
        src = img.get("src", "")
        if "qrserver" not in src and "qrcode" not in src:
            continue
        for data in parse_qs(urlparse(src).query).get("data", []):
            url = unquote(data)
            if NETDISK_RE.search(url) and url not in seen:
                seen.add(url)
                links.append(DownloadLink(f"{_netdisk_label(url)}（扫码）", url))
    for link in links:
        _extract_code(link)
    return links


def parse_article_html(html: str, hit: dict) -> Candidate:
    """解析文章页可见网盘链接；无链接时返回文章页作为入口。"""
    soup = BeautifulSoup(html, "html.parser")
    page_url = hit.get("page_url", "")
    links = _extract_download_links(soup, page_url)
    content = _content_container(soup)
    m = PASSWORD_RE.search(content.get_text(" ", strip=True) or html)
    password = m.group(1).strip() if m else ""
    if not links:
        links.append(DownloadLink("文章页", page_url))
    return Candidate(
        source="gamer520.com",
        title=hit.get("title", ""),
        page_url=page_url,
        kind="body",
        links=links,
        password=password,
    )


def extract_download_gate(html: str):
    """从文章/侧栏提取“获取资源/立即获取”的 post_id。"""
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.select(".go-down[data-id], .widget-pay .go-down[data-id]"):
        post_id = (a.get("data-id") or "").strip()
        if post_id.isdigit():
            return post_id
    return None


def extract_redirect_target(html: str):
    """解析 gamer520 跳转页里的 window.location 目标。"""
    m = REDIRECT_RE.search(html)
    return m.group(1).strip() if m else ""


def _admin_ajax_url(page_url: str) -> str:
    parsed = urlparse(page_url)
    return f"{parsed.scheme}://{parsed.netloc}/wp-admin/admin-ajax.php"


async def _request_gate_url(client, page_url: str, post_id: str):
    """模拟页面“获取资源”按钮，得到 /go 地址。"""
    url = _admin_ajax_url(page_url)
    headers = {
        "Referer": page_url,
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }
    data = {"action": "user_down_ajax", "post_id": post_id}
    for attempt in range(2):
        try:
            resp = await client.post(url, data=data, headers=headers)
            resp.raise_for_status()
            payload = json.loads(resp.text)
            if str(payload.get("status")) == "1":
                return str(payload.get("msg") or "").strip()
            return ""
        except (httpx.HTTPError, ValueError, TypeError):
            if attempt == 0:
                await asyncio.sleep(1.5)
    return ""


async def _resolve_hidden_links(
    client,
    page_url: str,
    html: str,
    depth: int = 0,
    seen: set | None = None,
):
    """跟随“立即获取”链路，尽量拿到真实网盘地址。"""
    if depth >= MAX_GATE_DEPTH:
        return []
    seen = seen or set()
    if page_url in seen:
        return []
    seen.add(page_url)
    post_id = extract_download_gate(html)
    if not post_id:
        return []
    gate_url = await _request_gate_url(client, page_url, post_id)
    if not gate_url:
        return []
    gate_url = urljoin(page_url, gate_url)
    if NETDISK_RE.search(gate_url):
        link = DownloadLink(_netdisk_label(gate_url), gate_url)
        _extract_code(link)
        return [link]
    await asyncio.sleep(random.uniform(0.8, 1.5))
    try:
        resp = await fetch(client, gate_url)
        target = extract_redirect_target(resp.text)
    except httpx.HTTPError:
        return []
    if not target:
        return []
    target = urljoin(gate_url, target)
    if NETDISK_RE.search(target):
        link = DownloadLink(_netdisk_label(target), target)
        _extract_code(link)
        return [link]
    if not ARTICLE_URL_RE.fullmatch(target):
        return []
    await asyncio.sleep(random.uniform(0.8, 1.5))
    try:
        target_html = (await fetch(client, target)).text
    except httpx.HTTPError:
        return []
    links = _extract_download_links(BeautifulSoup(target_html, "html.parser"), target)
    nested = await _resolve_hidden_links(
        client, target, target_html, depth + 1, seen
    )
    for link in nested:
        if link.url not in {existing.url for existing in links}:
            links.append(link)
    return links


async def search_gamer520(client, query: str):
    resp = await fetch(client, SEARCH_URL, params={"s": query})
    return parse_search_html(resp.text)


async def resolve_article(client, hit: dict) -> Candidate:
    await asyncio.sleep(random.uniform(0.8, 1.5))  # 反爬：请求间隔
    page_url = hit.get("page_url", "")
    resp = await fetch(client, page_url)
    candidate = parse_article_html(resp.text, hit)
    static_links = [link for link in candidate.links if link.url != page_url]
    hidden_links = []
    try:
        hidden_links = await _resolve_hidden_links(client, page_url, resp.text)
    except Exception:
        hidden_links = []
    merged = hidden_links + static_links
    unique = []
    seen = set()
    for link in merged:
        if link.url not in seen:
            seen.add(link.url)
            unique.append(link)
    candidate.links = unique or [DownloadLink("文章页", page_url)]
    return candidate


def fallback_candidate(hit: dict) -> Candidate:
    return Candidate(
        source="gamer520.com",
        title=hit.get("title", ""),
        page_url=hit.get("page_url", ""),
        kind="body",
        links=[DownloadLink("文章页", hit.get("page_url", ""))],
    )
