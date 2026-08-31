"""把搜索结果格式化为纯文本回复。"""

from __future__ import annotations


def _link_line(link) -> str:
    extra = f"（{link.extra}）" if link.extra else ""
    return f"   {link.label}: {link.url}{extra}"


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
        return " ".join(parts)

    lines = [f"为你找到《{query}》的下载信息：", ""]
    index = 1

    if of_candidates:
        lines.append("【全量游戏（含联机补丁）· online-fix.me】")
        for cand in of_candidates:
            lines.append(f"{index}. {cand.title}")
            lines.append(f"   详情页: {cand.page_url}")
            for link in cand.links[:3]:
                lines.append(_link_line(link))
            if cand.password:
                lines.append(f"   解压密码: {cand.password}")
            index += 1
        lines.append("")

    if g5_candidates:
        lines.append("【游戏本体 · gamer520.com】")
        for cand in g5_candidates:
            lines.append(f"{index}. {cand.title}")
            lines.append(f"   文章页: {cand.page_url}")
            for link in cand.links[:3]:
                lines.append(_link_line(link))
            if cand.password:
                lines.append(f"   解压密码: {cand.password}")
            index += 1
        if not of_candidates:
            lines.append("注：未找到对应的联机补丁。")
        lines.append("")

    if not report.onlinefix_ok:
        lines.append("online-fix.me 暂时无法访问，以上结果来自 gamer520.com。")
    if not report.gamer520_ok:
        lines.append("gamer520.com 暂时无法访问，以上结果来自 online-fix.me。")
    return "\n".join(lines).rstrip()
