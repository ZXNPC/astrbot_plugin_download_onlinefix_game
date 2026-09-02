"""JSON 文件缓存：搜索结果缓存，支持 TTL。"""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path


class SearchCache:
    def __init__(self, path, ttl_seconds: float):
        self.path = Path(path)
        self.ttl_seconds = float(ttl_seconds)
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> dict:
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("search"), dict):
                # 旧版本可能残留 names/translate 段，已不再使用，加载时丢弃。
                return {"search": data["search"]}
        except (OSError, ValueError):
            pass
        return {"search": {}}

    def _save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def _entry_fresh(self, entry) -> bool:
        if not isinstance(entry, dict) or "ts" not in entry or "value" not in entry:
            return False
        return time.time() - float(entry["ts"]) < self.ttl_seconds

    def get_search(self, key: str):
        with self._lock:
            entry = self._data.get("search", {}).get(key)
        if entry is not None and self._entry_fresh(entry):
            return entry["value"]
        return None

    def set_search(self, key: str, value) -> None:
        with self._lock:
            self._data.setdefault("search", {})[key] = {
                "ts": time.time(),
                "value": value,
            }
            self._save()

    def clear(self) -> None:
        """清空全部搜索缓存。"""
        with self._lock:
            self._data = {"search": {}}
            self._save()
