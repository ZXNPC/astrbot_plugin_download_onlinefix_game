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
