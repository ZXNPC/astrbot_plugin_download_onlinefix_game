import asyncio

from app import name_lookup
from app.cache import SearchCache
from app.service import GameDownloadService


def _service(tmp_path, **cfg):
    config = {"result_count": 3, "request_timeout": 60}
    config.update(cfg)
    return GameDownloadService(config, SearchCache(tmp_path / "cache.json", ttl_seconds=3600))


async def _noop_search(query, cache_key):
    return []


def test_search_flags_resolution_failure(tmp_path, monkeypatch):
    async def fake_resolve(term, *, timeout=10.0):
        return None

    monkeypatch.setattr(name_lookup, "resolve_english_name", fake_resolve)
    service = _service(tmp_path)
    monkeypatch.setattr(service, "_search_onlinefix", _noop_search)
    monkeypatch.setattr(service, "_search_gamer520", _noop_search)
    report = asyncio.run(service.search("渔力全开"))
    assert report.name_resolution_failed is True
    assert report.query == "渔力全开"


def test_search_caches_resolved_name(tmp_path, monkeypatch):
    async def fake_resolve(term, *, timeout=10.0):
        return "How to Fish"

    monkeypatch.setattr(name_lookup, "resolve_english_name", fake_resolve)
    service = _service(tmp_path)
    monkeypatch.setattr(service, "_search_onlinefix", _noop_search)
    monkeypatch.setattr(service, "_search_gamer520", _noop_search)
    report = asyncio.run(service.search("渔力全开"))
    assert report.name_resolution_failed is False
    assert service.cache.get_name("渔力全开") == "How to Fish"


def test_search_uses_cached_name_without_steam(tmp_path, monkeypatch):
    async def boom(term, *, timeout=10.0):
        raise AssertionError("不应再次调用 Steam")

    service = _service(tmp_path)
    service.cache.set_name("渔力全开", "How to Fish")
    monkeypatch.setattr(name_lookup, "resolve_english_name", boom)
    monkeypatch.setattr(service, "_search_onlinefix", _noop_search)
    monkeypatch.setattr(service, "_search_gamer520", _noop_search)
    report = asyncio.run(service.search("渔力全开"))
    assert report.name_resolution_failed is False


def test_search_skips_steam_for_english_query(tmp_path, monkeypatch):
    async def boom(term, *, timeout=10.0):
        raise AssertionError("英文查询不应调用 Steam")

    monkeypatch.setattr(name_lookup, "resolve_english_name", boom)
    service = _service(tmp_path)
    monkeypatch.setattr(service, "_search_onlinefix", _noop_search)
    monkeypatch.setattr(service, "_search_gamer520", _noop_search)
    report = asyncio.run(service.search("Cyberpunk 2077"))
    assert report.name_resolution_failed is False