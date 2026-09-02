"""把搜索结果格式化为纯文本回复。"""

from __future__ import annotations

from urllib.parse import urlparse

ALL_MISS_HINT = (
    "提示：若确认该游戏/补丁确实存在，可尝试中英文各搜一遍，"
    "如 /game <游戏中文名> 或 /game <游戏英文名>。"
)
OF_MISS_HINT = (
    "（提示：online-fix.me 未找到对应的联机补丁；若确认存在，"
    "可尝试用英文名再搜，如 /game <游戏英文名>）"
)
G5_MISS_HINT = (
    "（提示：gamer520.com 未找到对应的游戏本体；若确认存在，"
    "可尝试用中文名再搜，如 /game <游戏中文名>）"
)
ONLINEFIX_PAGE_GUIDE = (
    "下载指引：打开详情页后，在正文的“Версия игры / 游戏版本”附近"
    "找到一排蓝色方块下载按钮，直接点击即可：\n"
    "- Online-Fix Hosters / Online-Fix Drive：完整游戏（含联机补丁）\n"
    "- Фикс с сервера（服务器 Fix）：已有游戏本体时只下载联机补丁\n"
    "- Скачать Torrent：种子下载"
)


def _link_line(link) -> str:
    extra = f"（{link.extra}）" if link.extra else ""
    return f"   {link.label}: {link.url}{extra}"


def _display_links(cand):
    """过滤需要 Referer 的 online-fix.me 站内下载地址；旧缓存中的此类链接也一并过滤。"""
    if cand.source != "online-fix.me":
        return cand.links[:3]
    usable = []
    for link in cand.links:
        parsed = urlparse(link.url)
        host = (parsed.hostname or "").lower()
        guarded = host.endswith(".online-fix.me")
        if host == "online-fix.me":
            try:
                guarded = parsed.port == 2053
            except ValueError:
                guarded = False
        if not guarded:
            usable.append(link)
        if len(usable) == 3:
            break
    return usable


def format_report(report) -> str:
    query = report.query
    of_candidates = report.onlinefix_candidates
    g5_candidates = report.gamer520_candidates

    if not report.onlinefix_ok and not report.gamer520_ok:
        return f"暂时无法查询《{query}》的下载信息，请稍后再试。"

    if not of_candidates and not g5_candidates:
        parts = [f"未找到《{query}》的下载信息。"]
        if not report.onlinefix_ok:
            parts.append("（online-fix.me 暂时无法访问）")
        if not report.gamer520_ok:
            parts.append("（gamer520.com 暂时无法访问）")
        return f"{' '.join(parts)}\n{ALL_MISS_HINT}"

    numbered = len(of_candidates) + len(g5_candidates) > 1
    lines = [f"为你找到《{query}》的下载信息：", ""]
    index = 1

    if of_candidates:
        lines.append("【全量游戏（含联机补丁）· online-fix.me】")
        for cand in of_candidates:
            prefix = f"{index}. " if numbered else ""
            lines.append(f"{prefix}{cand.title}")
            lines.append(f"   详情页: {cand.page_url}")
            for link in _display_links(cand):
                lines.append(_link_line(link))
            if cand.password:
                lines.append(f"   解压密码: {cand.password}")
            index += 1
        lines.append("")
        lines.append(ONLINEFIX_PAGE_GUIDE)
        lines.append("")
        lines.append("")  # 让 online-fix.me 与 gamer520.com 两个分组在视觉上隔开

    if g5_candidates:
        lines.append("【游戏本体 · gamer520.com】")
        for cand in g5_candidates:
            prefix = f"{index}. " if numbered else ""
            lines.append(f"{prefix}{cand.title}")
            lines.append(f"   文章页: {cand.page_url}")
            for link in cand.links[:3]:
                lines.append(_link_line(link))
            if cand.password:
                lines.append(f"   解压密码: {cand.password}")
            index += 1
        lines.append("")

    if report.onlinefix_ok and not of_candidates and g5_candidates:
        lines.append(OF_MISS_HINT)
    if report.gamer520_ok and not g5_candidates and of_candidates:
        lines.append(G5_MISS_HINT)

    if not report.onlinefix_ok:
        lines.append("online-fix.me 暂时无法访问，以上结果来自 gamer520.com。")
    if not report.gamer520_ok:
        lines.append("gamer520.com 暂时无法访问，以上结果来自 online-fix.me。")
    return "\n".join(lines).rstrip()
