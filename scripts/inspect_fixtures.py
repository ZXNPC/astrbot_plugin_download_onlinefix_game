"""Dev utility: inspect downloaded site fixtures (not shipped with the plugin)."""

import re
from pathlib import Path

from bs4 import BeautifulSoup


FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def inspect_onlinefix_search():
    h = (FIXTURES / "onlinefix_search.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(h, "html.parser")
    items = soup.select("div.news.news-search div.article.clr")
    print("ONLINEFIX SEARCH ITEMS:", len(items))
    for item in items[:5]:
        title_el = item.select_one("h2.title")
        big = item.select_one("a.big-link")
        img = item.select_one("div.image img, img.lazyload, img")
        preview = item.select_one(".preview-text")
        print("- title:", title_el.get_text(strip=True) if title_el else None)
        print("  big-link:", big.get("href") if big else None)
        print("  img src/data-src:", (img.get("data-src") or img.get("src"))[:120] if img else None)
        print("  preview:", (preview.get_text(" ", strip=True)[:160] if preview else None))


def inspect_gamer520_search():
    h = (FIXTURES / "gamer520_search.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(h, "html.parser")
    print("\nGAMER520 SEARCH LEN:", len(h))
    links = [
        a
        for a in soup.select("a[href]")
        if re.fullmatch(r"https?://www\.gamer520\.com/\d+\.html", a.get("href", ""))
    ]
    seen = {}
    for a in links:
        if a["href"] not in seen:
            seen[a["href"]] = a.get_text(" ", strip=True)[:100]
    for url, text in list(seen.items())[:10]:
        print(url, "|", text)
    for cls in ["entry-title", "post-title", "article-title", "elementor-post__title", "entry-header", "page-header"]:
        els = soup.select(f".{cls}")
        if els:
            print("CLASS", cls, "->", [e.get_text(" ", strip=True)[:80] for e in els[:3]])
    # Common theme containers
    for sel in ["article", "main article", ".post", ".hentry", ".list-item", ".item"]:
        els = soup.select(sel)
        if els:
            print("SEL", sel, "count", len(els), "first:", els[0].get("class"))


def inspect_gamer520_article():
    h = (FIXTURES / "gamer520_article.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(h, "html.parser")
    print("\nGAMER520 ARTICLE TITLE:", soup.title.get_text(strip=True) if soup.title else None)
    pats = [
        r"pan\.xunlei\.com[^\"'\s<>]*",
        r"pan\.baidu\.com[^\"'\s<>]*",
        r"https?://[^\"'\s<>]*(?:quark|aliyundrive|123pan|weiyun|lanzou|ctfile|mega|mediafire|pixeldrain|gofile|modsfire|115\.com)[^\"'\s<>]*",
    ]
    for p in pats:
        found = list(dict.fromkeys(m.group(0).rstrip(".,;:") for m in re.finditer(p, h, re.I)))
        print(p[:25], "->", found[:6])
    # Show any pwd= occurrences
    pwd = list(dict.fromkeys(m.group(0) for m in re.finditer(r"pwd=[A-Za-z0-9]+", h)))
    print("pwd params:", pwd[:10])
    # Where do download links live? print anchor context around xunlei
    for m in list(re.finditer(r"pan\.xunlei\.com", h))[:2]:
        seg = h[max(0, m.start() - 500): m.start() + 300]
        print("CTX:", re.sub(r"\s+", " ", seg)[-450:])
    # All anchors around download cards
    print("\n--- anchors with netdisk-ish hrefs ---")
    for a in soup.select("a[href]"):
        href = a.get("href", "")
        if re.search(r"pan\.(xunlei|baidu)|quark|aliyundrive|123pan|lanzou|ctfile|mega|mediafire|pixeldrain|gofile|modsfire|115\.com|weiyun|tianyancha", href, re.I):
            txt = a.get_text(" ", strip=True)[:60]
            print(repr(href[:160]), "|", txt)
    # bdp card titles
    print("\n--- bdp cards ---")
    for card in soup.select(".bdp-card, [class*='bdp-card']"):
        t = card.select_one(".bdp-card-title")
        btn = card.select_one("a.bdp-btn")
        pwd_box = card.select_one(".bdp-pwd-box")
        print("card:", t.get_text(strip=True) if t else None, "| btn:", btn.get("href") if btn else None, "| pwd-box:", (pwd_box.get_text(" ", strip=True)[:60] if pwd_box else None))
    # context around baidu and quark encoded links
    for needle in ["pan.baidu.com%2F", "pan.quark.cn", "qrserver"]:
        for m in list(re.finditer(re.escape(needle), h))[:1]:
            seg = h[max(0, m.start() - 700): m.start() + 250]
            print(f"\nCTX[{needle}]:", re.sub(r"\s+", " ", seg))


def inspect_onlinefix_detail():
    h = (FIXTURES / "onlinefix_detail.html").read_text(encoding="utf-8")
    soup = BeautifulSoup(h, "html.parser")
    print("\nONLINEFIX DETAIL TITLE:", soup.title.get_text(strip=True) if soup.title else None)
    print("H1:", soup.select_one("h1").get_text(strip=True) if soup.select_one("h1") else None)
    btns = soup.select("a.btn, a[href]")
    print("BTN COUNT:", len(btns))
    seen = set()
    for a in btns:
        href = a.get("href", "")
        text = a.get_text(" ", strip=True)[:70]
        key = (href, text)
        if key in seen:
            continue
        seen.add(key)
        if href or text:
            print("-", repr(href[:150]), "|", repr(text))
    # full-story content download section
    content = soup.select_one(".full-story-content")
    if content:
        print("\nFULL-STORY CONTENT download-ish text:")
        for el in content.select("a[href]"):
            print("  a:", repr(el.get("href", "")[:150]), "|", repr(el.get_text(" ", strip=True)[:60]))
    # scan for uploads/drive/hosters links
    import re
    for pat in ["uploads.online-fix.me", "drive.online-fix.me", "online-fix.me:2053", "pixeldrain", "drive.google", "mega.nz", "mediafire", "buzzheavier", "1fichier", "gofile", "modsfire"]:
        ms = list(dict.fromkeys(m.group(0) for m in re.finditer(r"https?://[^\"'\s<>]*(?:" + re.escape(pat) + r")[^\"'\s<>]*", h)))
        if ms:
            print("PAT", pat, "->", [u[:150] for u in ms[:4]])


if __name__ == "__main__":
    inspect_onlinefix_search()
    inspect_gamer520_search()
    inspect_gamer520_article()
    inspect_onlinefix_detail()
