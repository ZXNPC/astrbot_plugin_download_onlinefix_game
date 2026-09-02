import asyncio

from app.cache import SearchCache
from app.service import GameDownloadService, SEARCH_CACHE_VERSION


def _service(tmp_path, **cfg):
    config = {"result_count": 3, "request_timeout": 60}
    config.update(cfg)
    return GameDownloadService(config, SearchCache(tmp_path / "cache.json", ttl_seconds=3600))


async def _noop_search(query, cache_key):
    return []


def test_search_uses_raw_term_for_both_sources(tmp_path, monkeypatch):
    calls = []

    async def fake_onlinefix(query, cache_key):
        calls.append(("onlinefix", query, cache_key))
        return []

    async def fake_gamer520(query, cache_key):
        calls.append(("gamer520", query, cache_key))
        return []

    service = _service(tmp_path)
    monkeypatch.setattr(service, "_search_onlinefix", fake_onlinefix)
    monkeypatch.setattr(service, "_search_gamer520", fake_gamer520)
    report = asyncio.run(service.search("渔力全开"))
    assert report.query == "渔力全开"
    suffix = f":v{SEARCH_CACHE_VERSION}"
    assert sorted(calls) == sorted(
        [
            ("onlinefix", "渔力全开", f"渔力全开{suffix}:onlinefix"),
            ("gamer520", "渔力全开", f"渔力全开{suffix}:gamer520"),
        ]
    )
    assert report.onlinefix_ok is True
    assert report.gamer520_ok is True


def test_search_passes_english_query_unchanged(tmp_path, monkeypatch):
    calls = []

    async def fake_onlinefix(query, cache_key):
        calls.append(query)
        return []

    async def fake_gamer520(query, cache_key):
        calls.append(query)
        return []

    service = _service(tmp_path)
    monkeypatch.setattr(service, "_search_onlinefix", fake_onlinefix)
    monkeypatch.setattr(service, "_search_gamer520", fake_gamer520)
    asyncio.run(service.search("Cyberpunk 2077"))
    assert set(calls) == {"Cyberpunk 2077"}
    assert len(calls) == 2


def test_search_marks_source_failure(tmp_path, monkeypatch):
    async def boom(query, cache_key):
        raise RuntimeError("network timeout")

    service = _service(tmp_path)
    monkeypatch.setattr(service, "_search_onlinefix", boom)
    monkeypatch.setattr(service, "_search_gamer520", _noop_search)
    report = asyncio.run(service.search("赛博朋克2077"))
    assert report.onlinefix_ok is False
    assert "RuntimeError" in report.onlinefix_error
    assert report.gamer520_ok is True
