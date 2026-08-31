"""JSON 文件缓存：搜索结果与翻译结果，支持 TTL。"""

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
            if isinstance(data, dict):
                return data
        except (OSError, ValueError):
            pass
        return {"search": {}, "translate": {}}

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

    def get_translation(self, text: str):
        with self._lock:
            entry = self._data.get("translate", {}).get(text)
        if entry is not None and self._entry_fresh(entry):
            return entry["value"]
        return None

    def set_translation(self, text: str, value: str) -> None:
        with self._lock:
            self._data.setdefault("translate", {})[text] = {
                "ts": time.time(),
                "value": value,
            }
            self._save()
