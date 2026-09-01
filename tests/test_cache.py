import json
import time

from app.cache import SearchCache


def test_cache_roundtrip(tmp_path):
    cache = SearchCache(tmp_path / "cache.json", ttl_seconds=3600)
    assert cache.get_search("k") is None
    cache.set_search("k", [{"a": 1}])
    assert cache.get_search("k") == [{"a": 1}]


def test_cache_expiry(tmp_path):
    cache = SearchCache(tmp_path / "cache.json", ttl_seconds=0.05)
    cache.set_search("k", [1])
    time.sleep(0.1)
    assert cache.get_search("k") is None


def test_cache_reload(tmp_path):
    cache = SearchCache(tmp_path / "cache.json", ttl_seconds=3600)
    cache.set_search("k", [1])
    cache2 = SearchCache(tmp_path / "cache.json", ttl_seconds=3600)
    assert cache2.get_search("k") == [1]


def test_cache_names_roundtrip(tmp_path):
    cache = SearchCache(tmp_path / "cache.json", ttl_seconds=3600)
    assert cache.get_name("渔力全开") is None
    cache.set_name("渔力全开", "How to Fish")
    assert cache.get_name("渔力全开") == "How to Fish"
    cache2 = SearchCache(tmp_path / "cache.json", ttl_seconds=3600)
    assert cache2.get_name("渔力全开") == "How to Fish"


def test_cache_clear(tmp_path):
    cache = SearchCache(tmp_path / "cache.json", ttl_seconds=3600)
    cache.set_search("k", [1])
    cache.set_name("渔力全开", "How to Fish")
    cache.clear()
    assert cache.get_search("k") is None
    assert cache.get_name("渔力全开") is None
    cache2 = SearchCache(tmp_path / "cache.json", ttl_seconds=3600)
    assert cache2.get_search("k") is None
    assert cache2.get_name("渔力全开") is None


def test_cache_migrates_translate_section(tmp_path):
    now = time.time()
    p = tmp_path / "cache.json"
    p.write_text(
        json.dumps(
            {
                "search": {"a": {"ts": now, "value": [1]}},
                "translate": {"渔力全开": {"ts": now, "value": "How to Fish"}},
            }
        ),
        encoding="utf-8",
    )
    cache = SearchCache(p, ttl_seconds=3600)
    assert cache.get_name("渔力全开") == "How to Fish"
    assert cache.get_search("a") == [1]
    assert "translate" not in cache._data
    assert "names" in cache._data