import pathlib
import re

from app import gamer520, online_fix

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def read(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_onlinefix_search_parser():
    hits = online_fix.parse_search_html(read("onlinefix_search.html"))
    assert len(hits) == 1
    assert "CyberCorp" in hits[0]["title"]
    assert "/games/adventures/17754-cybercorp-po-seti.html" in hits[0]["page_url"]


def test_onlinefix_detail_parser():
    hit = {
        "title": "CyberCorp по сети",
        "page_url": "https://online-fix.me/games/adventures/17754-cybercorp-po-seti.html",
    }
    cand = online_fix.parse_detail_html(read("onlinefix_detail.html"), hit)
    assert cand.kind == "full"
    assert cand.password == "online-fix.me"
    urls = [link.url for link in cand.links]
    assert any("uploads.online-fix.me" in u for u in urls)
    assert any("drive.online-fix.me" in u for u in urls)
    assert any("hosters.online-fix.me" in u for u in urls)


def test_gamer520_search_parser():
    hits = gamer520.parse_search_html(read("gamer520_search.html"))
    assert len(hits) >= 10
    for hit in hits:
        assert re.fullmatch(r"https?://www\.gamer520\.com/\d+\.html", hit["page_url"])
        assert hit["title"]


def test_gamer520_article_parser():
    hit = {
        "title": "超英派遣中心 Dispatch",
        "page_url": "https://www.gamer520.com/105821.html",
    }
    cand = gamer520.parse_article_html(read("gamer520_article.html"), hit)
    urls = [link.url for link in cand.links]
    assert any("pan.xunlei.com" in u for u in urls)
    assert any("pan.baidu.com" in u for u in urls)
    assert any("pan.quark.cn" in u for u in urls)
    assert cand.password == "laoquzhang.com"
    assert any(link.extra for link in cand.links)
