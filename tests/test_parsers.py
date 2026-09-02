import asyncio
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
    # fixture 只含需 Referer 的站内下载入口，详情页外直接打开会 401
    assert cand.links == []


def test_onlinefix_guarded_url_classification():
    assert online_fix.is_onlinefix_guarded_url(
        "https://uploads.online-fix.me:2053/uploads/Game/"
    )
    assert online_fix.is_onlinefix_guarded_url("https://drive.online-fix.me:2053/Game")
    assert online_fix.is_onlinefix_guarded_url(
        "https://hosters.online-fix.me:2053/Game"
    )
    assert not online_fix.is_onlinefix_guarded_url(
        "https://online-fix.me/games/1-game.html"
    )
    assert not online_fix.is_onlinefix_guarded_url("https://mega.nz/file/abc")


def test_onlinefix_detail_parser_keeps_external_netdisk():
    hit = {
        "title": "Game по сети",
        "page_url": "https://online-fix.me/games/1-game.html",
    }
    html = """
<a href="https://uploads.online-fix.me:2053/uploads/Game/">server</a>
<a href="https://mega.nz/file/abc">mega</a>
"""
    cand = online_fix.parse_detail_html(html, hit)
    assert [link.url for link in cand.links] == ["https://mega.nz/file/abc"]


def test_gamer520_search_parser():
    hits = gamer520.parse_search_html(read("gamer520_search.html"))
    assert len(hits) >= 10
    for hit in hits:
        assert re.fullmatch(r"https?://(?:www\.)?(?:gamer520|gamers520)\.com/\d+\.html", hit["page_url"])
        assert hit["title"]


def test_gamer520_search_parser_skips_non_game_categories():
    html = """
<article class="post">
  <span class="meta-category"><a href="https://www.gamer520.com/xgq">修改器</a></span>
  <h2 class="entry-title"><a href="https://www.gamer520.com/108170.html">幸福工厂|修改器</a></h2>
</article>
<article class="post">
  <span class="meta-category"><a href="https://www.gamer520.com/pcplay">PC PLAY</a></span>
  <h2 class="entry-title"><a href="https://www.gamer520.com/45746.html">幸福工厂 正式版</a></h2>
</article>
"""
    hits = gamer520.parse_search_html(html)
    assert [hit["page_url"] for hit in hits] == ["https://www.gamer520.com/45746.html"]


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


def test_gamer520_download_gate_and_redirect_helpers():
    html = '<div class="widget-pay"><a class="go-down" data-id="45746">获取资源</a></div>'
    assert gamer520.extract_download_gate(html) == "45746"
    assert gamer520.extract_download_gate("<article></article>") is None
    go_page = "<script>window.location='https://pan.quark.cn/s/abc';</script>"
    assert (
        gamer520.extract_redirect_target(go_page)
        == "https://pan.quark.cn/s/abc"
    )


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        return None


def test_gamer520_resolve_article_follows_hidden_gate(monkeypatch):
    page_url = "https://www.gamer520.com/45746.html"
    article_html = """
<article>
  <div class="entry-content"><p><strong>解压密码:laoquzhang.com</strong></p></div>
</article>
<div class="widget-pay"><a class="go-down" data-id="45746">获取资源</a></div>
"""
    go_html = "<script>window.location='https://pan.quark.cn/s/abc';</script>"

    class _FakeClient:
        async def post(self, url, data=None, headers=None):
            assert data == {"action": "user_down_ajax", "post_id": "45746"}
            return _FakeResponse('{"status":"1","msg":"/go?post_id=45746"}')

    async def fake_fetch(client, url, **kwargs):
        if url == page_url:
            return _FakeResponse(article_html)
        return _FakeResponse(go_html)

    monkeypatch.setattr(gamer520, "fetch", fake_fetch)
    monkeypatch.setattr(gamer520.random, "uniform", lambda *_: 0)
    cand = asyncio.run(
        gamer520.resolve_article(
            _FakeClient(),
            {"title": "幸福工厂 正式版", "page_url": page_url},
        )
    )
    assert cand.links[0].url == "https://pan.quark.cn/s/abc"
    assert cand.password == "laoquzhang.com"
