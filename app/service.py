"""搜索编排：并行查询两个来源、缓存、超时与候选排序。"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from . import gamer520, name_lookup, online_fix
from .cache import SearchCache
from .http_client import build_client
from .matcher import normalize, rank_hits
from .result import candidate_from_dict, candidate_to_dict

logger = logging.getLogger(__name__)


@dataclass
class SearchReport:
    query: str
    onlinefix_candidates: list = field(default_factory=list)
    gamer520_candidates: list = field(default_factory=list)
    onlinefix_ok: bool = True
    gamer520_ok: bool = True
    onlinefix_error: str = ""
    gamer520_error: str = ""
    name_resolution_failed: bool = False


class GameDownloadService:
    def __init__(self, config, cache: SearchCache):
        self.result_count = max(1, int(config.get("result_count", 3)))
        self.timeout = max(1.0, float(config.get("request_timeout", 60)))
        self.cache = cache

    async def _resolve_english_name(self, game_name: str):
        """Steam 名称解析；返回 (英文查询词, 是否成功)。失败时退回原词。"""
        if not name_lookup.contains_cjk(game_name):
            return game_name, True
        cached = self.cache.get_name(game_name)
        if cached:
            return cached, True
        try:
            en = await name_lookup.resolve_english_name(
                game_name, timeout=min(self.timeout, 20.0)
            )
        except Exception as exc:
            logger.warning(f"Steam 名称解析失败，退回原词继续搜索: {exc}")
            en = None
        if en:
            self.cache.set_name(game_name, en)
            return en, True
        return game_name, False

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
        key = normalize(game_name)
        en_query, resolved = await self._resolve_english_name(game_name)
        results = await asyncio.gather(
            asyncio.wait_for(
                self._search_onlinefix(en_query, f"{key}:onlinefix"),
                timeout=self.timeout,
            ),
            asyncio.wait_for(
                self._search_gamer520(game_name, f"{key}:gamer520"),
                timeout=self.timeout,
            ),
            return_exceptions=True,
        )
        report = SearchReport(
            query=game_name.strip(), name_resolution_failed=not resolved
        )
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