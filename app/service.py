"""搜索编排：并行查询两个来源、缓存、超时与候选排序。"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from . import gamer520, online_fix
from .cache import SearchCache
from .http_client import build_client
from .matcher import normalize, rank_hits
from .result import candidate_from_dict, candidate_to_dict

logger = logging.getLogger(__name__)

# 解析策略变更时递增，避免命中上一版缓存的旧链接结构。
SEARCH_CACHE_VERSION = 2


@dataclass
class SearchReport:
    query: str
    onlinefix_candidates: list = field(default_factory=list)
    gamer520_candidates: list = field(default_factory=list)
    onlinefix_ok: bool = True
    gamer520_ok: bool = True
    onlinefix_error: str = ""
    gamer520_error: str = ""


class GameDownloadService:
    def __init__(self, config, cache: SearchCache):
        self.result_count = max(1, int(config.get("result_count", 3)))
        self.timeout = max(1.0, float(config.get("request_timeout", 60)))
        self.cache = cache

    async def _search_onlinefix(self, query: str, cache_key: str):
        cached = self.cache.get_search(cache_key)
        if cached is not None:
            return [candidate_from_dict(item) for item in cached]
        async with build_client(self.timeout) as client:
            hits = await online_fix.search_onlinefix(client, query)
            ranked = rank_hits(hits, query, self.result_count)
            candidates = []
            for hit in ranked:
                try:
                    candidates.append(await online_fix.resolve_detail(client, hit))
                except Exception:
                    candidates.append(online_fix.fallback_candidate(hit))
        self.cache.set_search(cache_key, [candidate_to_dict(c) for c in candidates])
        return candidates

    async def _search_gamer520(self, query: str, cache_key: str):
        cached = self.cache.get_search(cache_key)
        if cached is not None:
            return [candidate_from_dict(item) for item in cached]
        async with build_client(self.timeout) as client:
            hits = await gamer520.search_gamer520(client, query)
            ranked = rank_hits(hits, query, self.result_count)
            candidates = []
            for hit in ranked:
                try:
                    candidates.append(await gamer520.resolve_article(client, hit))
                except Exception:
                    candidates.append(gamer520.fallback_candidate(hit))
        self.cache.set_search(cache_key, [candidate_to_dict(c) for c in candidates])
        return candidates

    async def search(self, game_name: str) -> SearchReport:
        """两个来源均使用用户请求原词检索，不做中英文名转换。"""
        key = normalize(game_name)
        cache_base = f"{key}:v{SEARCH_CACHE_VERSION}"
        results = await asyncio.gather(
            asyncio.wait_for(
                self._search_onlinefix(game_name, f"{cache_base}:onlinefix"),
                timeout=self.timeout,
            ),
            asyncio.wait_for(
                self._search_gamer520(game_name, f"{cache_base}:gamer520"),
                timeout=self.timeout,
            ),
            return_exceptions=True,
        )
        report = SearchReport(query=game_name.strip())
        onlinefix_result, gamer520_result = results
        if isinstance(onlinefix_result, Exception):
            report.onlinefix_ok = False
            report.onlinefix_error = f"{type(onlinefix_result).__name__}: {onlinefix_result}"
        else:
            report.onlinefix_candidates = onlinefix_result
        if isinstance(gamer520_result, Exception):
            report.gamer520_ok = False
            report.gamer520_error = f"{type(gamer520_result).__name__}: {gamer520_result}"
        else:
            report.gamer520_candidates = gamer520_result
        return report
