"""搜索结果的数据结构。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class DownloadLink:
    label: str
    url: str
    extra: str = ""


@dataclass
class Candidate:
    source: str
    title: str
    page_url: str
    kind: str  # "full" 全量游戏 / "body" 游戏本体
    links: List[DownloadLink] = field(default_factory=list)
    password: str = ""
    score: float = 0.0


def candidate_to_dict(candidate: Candidate) -> dict:
    return {
        "source": candidate.source,
        "title": candidate.title,
        "page_url": candidate.page_url,
        "kind": candidate.kind,
        "password": candidate.password,
        "score": candidate.score,
        "links": [
            {"label": link.label, "url": link.url, "extra": link.extra}
            for link in candidate.links
        ],
    }


def candidate_from_dict(data: dict) -> Candidate:
    return Candidate(
        source=data.get("source", ""),
        title=data.get("title", ""),
        page_url=data.get("page_url", ""),
        kind=data.get("kind", ""),
        password=data.get("password", ""),
        score=float(data.get("score", 0.0)),
        links=[
            DownloadLink(
                link.get("label", "网盘"),
                link.get("url", ""),
                link.get("extra", ""),
            )
            for link in data.get("links", [])
        ],
    )
